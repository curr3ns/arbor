#!/usr/bin/env python3
"""Render the implementation summary page from a JSON data file and serve it on localhost.

Usage: build_report.py <report.json> [--port N] [--no-serve] [--no-open]
Serves the pages with server.py, which also runs the page's action buttons (commit & push, rerun, and test-management
publishing when the report names a test-management mapping). Never pushes by itself.
Output: ~/.arbor-reports/<TICKET>/index.html plus an all-tickets index.html (override root with ARBOR_REPORT_ROOT)
Data schema: see ../references/report.md. Diffs are computed here through the report's VCS mapping (vcs.py), not supplied.
"""
import hashlib, shutil, time, html, json, re, os, secrets, signal, subprocess, sys, socket, datetime
from pathlib import Path
from string import Template

sys.path.insert(0, str(Path(__file__).parent))
import vcs

T = Path(__file__).parent / "templates"
SERVER_VERSION = 12
tpl = lambda n: Template((T / n).read_text())
esc = lambda s: html.escape(str(s if s is not None else ""))

def base_branch(r):
    """The repo's baseBranch, else the remote's default branch."""
    base = r.get("baseBranch") or vcs.out(r["path"], "default_branch").strip()
    if not base:
        raise SystemExit(f"{r['name']}: no baseBranch and the VCS mapping could not find the default branch")
    return base

def report_url(d, port):
    """Where the ticket page is opened: the report's reportUrl template ({ticket}, {port}), else the local server."""
    return (d.get("reportUrl") or "http://localhost:{port}/{ticket}/").format(ticket=d["ticket"], port=port)

def _intra(old, new):
    """Wrap the differing middle of a changed line pair in <mark>; returns escaped (old, new)."""
    i = 0
    n = min(len(old), len(new))
    while i < n and old[i] == new[i]:
        i += 1
    j = 0
    while j < n - i and old[len(old) - 1 - j] == new[len(new) - 1 - j]:
        j += 1
    if i + j == 0 or (i == len(old) and j == 0 and i == len(new)):
        return esc(old), esc(new)
    wrap = lambda t: esc(t[:i]) + ("<mark>" + esc(t[i:len(t) - j]) + "</mark>" if len(t) - j > i else "") + esc(t[len(t) - j:])
    return wrap(old), wrap(new)

def parse_diff(text):
    """Split a unified diff (with "diff --git a/ b/" file headers) into files: [{path, old, status, adds, dels, rows}]; rows = (kind, oldno, newno, text|None)."""
    files, cur, o, n = [], None, 0, 0
    for line in text.splitlines():
        if line.startswith("diff --git "):
            m = re.match(r"diff --git a/(.*) b/(.*)$", line)
            cur = {"path": m.group(2) if m else line[11:], "old": m.group(1) if m else "", "status": "modified", "adds": 0, "dels": 0, "rows": []}
            files.append(cur)
        elif cur is None:
            continue
        elif line.startswith("@@"):
            m = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@(.*)", line)
            o, n = (int(m.group(1)), int(m.group(2))) if m else (0, 0)
            cur["rows"].append(("hunk", None, None, line))
        elif line.startswith("new file"):
            cur["status"] = "added"
        elif line.startswith("deleted file"):
            cur["status"] = "deleted"
        elif line.startswith("rename to"):
            cur["status"] = "renamed"
        elif line.startswith(("index ", "--- ", "+++ ", "old mode", "new mode", "similarity", "rename from", "Binary")) and not cur["rows"]:
            if line.startswith("Binary"):
                cur["rows"].append(("meta", None, None, line))
        elif line.startswith("+"):
            cur["adds"] += 1; cur["rows"].append(("add", None, n, line[1:])); n += 1
        elif line.startswith("-"):
            cur["dels"] += 1; cur["rows"].append(("del", o, None, line[1:])); o += 1
        elif line.startswith("\\"):
            cur["rows"].append(("meta", None, None, line))
        else:
            cur["rows"].append(("ctx", o, n, line[1:])); o += 1; n += 1
    return files

def _pairs(rows):
    """Yield display rows with intra-line marks: (kind, oldno, newno, html). Pairs del/add runs of equal length."""
    out, i = [], 0
    while i < len(rows):
        if rows[i][0] == "del":
            j = i
            while j < len(rows) and rows[j][0] == "del": j += 1
            k = j
            while k < len(rows) and rows[k][0] == "add": k += 1
            dels, adds = rows[i:j], rows[j:k]
            if len(dels) == len(adds):
                for d, a in zip(dels, adds):
                    od, na = _intra(d[3], a[3])
                    out.append(("del", d[1], None, od)); out.append(("add", None, a[2], na))
                # keep del block then add block ordering (paired marks computed above)
                ds = [x for x in out[-2 * len(dels):] if x[0] == "del"]; as_ = [x for x in out[-2 * len(dels):] if x[0] == "add"]
                del out[-2 * len(dels):]; out += ds + as_
            else:
                out += [("del", d[1], None, esc(d[3])) for d in dels] + [("add", None, a[2], esc(a[3])) for a in adds]
            i = k
        else:
            r = rows[i]; out.append((r[0], r[1], r[2], esc(r[3]))); i += 1
    return out

TM_ROOT = Path("~/.claude/arbor/providers/tests").expanduser()
TM_DEFAULTS = {
    "label": "Test management",
    "specPattern": r"\.(spec|test)\.[jt]sx?$",
    "testPattern": r"""\b(?:test|it)(?:\.(?:only|skip|fixme|fail|slow))?\(\s*(['"`])(.*?)\1""",
}

def test_mgmt(d):
    """The report's test-management mapping (its "testManagement" field: a name under TM_ROOT or a path), or None.
    Keys: label, skill, helper, helperUsage, tokenEnv, keyPattern (one capture group: the key), keyFormat ("{key}" template
    for display and titles), specPattern (which changed files are automated specs), testPattern (group 2: a test's title)."""
    name = d.get("testManagement")
    if not name:
        return None
    p = Path(os.path.expanduser(name)) if "/" in name else TM_ROOT / f"{name}.json"
    try:
        tm = {**TM_DEFAULTS, **json.loads(p.read_text())}
    except (OSError, ValueError) as e:
        raise SystemExit(f"cannot read the test-management mapping {p}: {e}")
    if not tm.get("keyPattern"):
        raise SystemExit(f"the test-management mapping {p} has no keyPattern")
    return tm

def tm_key(tm, key):
    return tm.get("keyFormat", "{key}").format(key=key)

def tm_tests(src, tm):
    """[(title, key|None)] for each test in a spec source; a test is published once its title carries a key."""
    out = []
    for m in re.finditer(tm["testPattern"], src or ""):
        k = re.search(tm["keyPattern"], m.group(2))
        out.append((m.group(2), k.group(1) if k else None))
    return out

def zrow(title, key, path, cols, tm):
    if key:
        inner = f'<span class="zi ok">&#10003;</span><span>Published to {esc(tm["label"])} as <code>{esc(tm_key(tm, key))}</code></span>'
        cls = "ok"
    else:
        inner = (f'<span class="zi warn">&#9888;</span><span>Not published to {esc(tm["label"])}</span>'
                 f'<button type="button" class="zbtn" data-zaction="tm-automation" data-file="{esc(path)}" data-title="{esc(title)}">Publish this test</button>')
        cls = "warn"
    return f'<tr class="zrow"><td colspan="{cols}"><div class="zbar {cls}">{inner}</div></td></tr>'

def tree_key(path):
    parts = path.split("/")
    return [(0, x.lower()) for x in parts[:-1]] + [(1, parts[-1].lower())]

ICON = {
    "dir": '<svg class="ic dir" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><path fill="currentColor" d="M1.75 1A1.75 1.75 0 0 0 0 2.75v10.5C0 14.216.784 15 1.75 15h12.5A1.75 1.75 0 0 0 16 13.25v-8.5A1.75 1.75 0 0 0 14.25 3H7.5a.25.25 0 0 1-.2-.1l-.9-1.2C6.07 1.26 5.55 1 5 1H1.75Z"/></svg>',
    "added": '<svg class="ic st added" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><path fill="currentColor" d="M2 1.75C2 .784 2.784 0 3.75 0h6.586c.464 0 .909.184 1.237.513l2.914 2.914c.329.328.513.773.513 1.237v9.586A1.75 1.75 0 0 1 13.25 16h-9.5A1.75 1.75 0 0 1 2 14.25Zm1.75-.25a.25.25 0 0 0-.25.25v12.5c0 .138.112.25.25.25h9.5a.25.25 0 0 0 .25-.25V6h-2.75A1.75 1.75 0 0 1 9 4.25V1.5Zm6.75.062V4.25c0 .138.112.25.25.25h2.688l-.011-.013-2.914-2.914ZM8 7a.75.75 0 0 1 .75.75v1.5h1.5a.75.75 0 0 1 0 1.5h-1.5v1.5a.75.75 0 0 1-1.5 0v-1.5h-1.5a.75.75 0 0 1 0-1.5h1.5v-1.5A.75.75 0 0 1 8 7Z"/></svg>',
    "deleted": '<svg class="ic st deleted" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><path fill="currentColor" d="M2 1.75C2 .784 2.784 0 3.75 0h6.586c.464 0 .909.184 1.237.513l2.914 2.914c.329.328.513.773.513 1.237v9.586A1.75 1.75 0 0 1 13.25 16h-9.5A1.75 1.75 0 0 1 2 14.25Zm1.75-.25a.25.25 0 0 0-.25.25v12.5c0 .138.112.25.25.25h9.5a.25.25 0 0 0 .25-.25V6h-2.75A1.75 1.75 0 0 1 9 4.25V1.5Zm6.75.062V4.25c0 .138.112.25.25.25h2.688l-.011-.013-2.914-2.914ZM6 10.75a.75.75 0 0 1 .75-.75h2.5a.75.75 0 0 1 0 1.5h-2.5a.75.75 0 0 1-.75-.75Z"/></svg>',
    "modified": '<svg class="ic st modified" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><path fill="currentColor" d="M2 1.75C2 .784 2.784 0 3.75 0h6.586c.464 0 .909.184 1.237.513l2.914 2.914c.329.328.513.773.513 1.237v9.586A1.75 1.75 0 0 1 13.25 16h-9.5A1.75 1.75 0 0 1 2 14.25Zm1.75-.25a.25.25 0 0 0-.25.25v12.5c0 .138.112.25.25.25h9.5a.25.25 0 0 0 .25-.25V6h-2.75A1.75 1.75 0 0 1 9 4.25V1.5Zm6.75.062V4.25c0 .138.112.25.25.25h2.688l-.011-.013-2.914-2.914ZM8 7a.75.75 0 0 1 .75.75V9h1.5a.75.75 0 0 1 0 1.5h-1.5v1.25a.75.75 0 0 1-1.5 0V10.5h-1.5a.75.75 0 0 1 0-1.5h1.5V7.75A.75.75 0 0 1 8 7Z" opacity="0"/><path fill="currentColor" d="M5.5 8a.75.75 0 0 1 .75-.75h3.5a.75.75 0 0 1 0 1.5h-3.5A.75.75 0 0 1 5.5 8Zm.75 2.25h3.5a.75.75 0 0 1 0 1.5h-3.5a.75.75 0 0 1 0-1.5Z" opacity="0"/><path fill="currentColor" d="M8 7.25a.75.75 0 0 1 .75.75v.75h.75a.75.75 0 0 1 0 1.5h-.75v.75a.75.75 0 0 1-1.5 0v-.75H6.5a.75.75 0 0 1 0-1.5h.75V8A.75.75 0 0 1 8 7.25ZM6.5 12h3a.75.75 0 0 1 0 1.5h-3a.75.75 0 0 1 0-1.5Z"/></svg>',
}
ICON["renamed"] = ICON["modified"]

def render_tree(files, rid, zinfo=None, tm=None):
    """Directory tree: collapsible folders, single-child folder chains merged ("common/src")."""
    zinfo = zinfo or {}
    root = {"dirs": {}, "files": []}
    for i, f in enumerate(files):
        node = root
        for part in f["path"].split("/")[:-1]:
            node = node["dirs"].setdefault(part, {"dirs": {}, "files": []})
        node["files"].append((i, f))

    def leaf(i, f):
        z = zinfo.get(f["path"])
        zb = ""
        if z and z[0]:
            ok = z[1] == z[0]
            zb = f'<span class="zbadge tiny {"ok" if ok else "warn"}" title="{z[1]} of {z[0]} tests published to {esc(tm["label"])}">{"&#10003;" if ok else "&#9888;"} {z[1]}/{z[0]}</span>'
        name = f["path"].rpartition("/")[2]
        unc = '<span class="udot" title="Uncommitted changes"></span>' if f.get("dirty") else ""
        return (f'<a class="ti" href="#{rid}-f{i}" data-target="{rid}-f{i}" data-path="{esc(f["path"].lower())}" title="{esc(f["path"])}">'
                f'{ICON.get(f["status"], ICON["modified"])}<span class="tn">{esc(name)}</span>{zb}{unc}'
                f'<span class="fstat"><span class="a">+{f["adds"]}</span> <span class="r">&minus;{f["dels"]}</span></span></a>')

    def walk(node):
        out = []
        for name in sorted(node["dirs"], key=str.lower):
            child, label = node["dirs"][name], name
            while len(child["dirs"]) == 1 and not child["files"]:
                (n2, c2), = child["dirs"].items()
                label, child = label + "/" + n2, c2
            out.append(f'<details class="td" open><summary><span class="chev"></span>{ICON["dir"]}<span class="tn">{esc(label)}</span></summary><div class="tc">{walk(child)}</div></details>')
        out += [leaf(i, f) for i, f in sorted(node["files"], key=lambda x: x[1]["path"].lower())]
        return "".join(out)
    return walk(root)

def md_inline(t):
    t = esc(t)
    codes = []
    def stash(m):
        codes.append(m.group(1)); return f"\x00{len(codes) - 1}\x00"
    t = re.sub(r"`([^`]+)`", stash, t)
    t = re.sub(r"\*\*([^*]+)\*\*|__([^_]+)__", lambda m: f"<b>{m.group(1) or m.group(2)}</b>", t)
    t = re.sub(r"(?<![*\w])\*([^*\s][^*]*?)\*(?![*\w])", r"<i>\1</i>", t)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', t)
    return re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{codes[int(m.group(1))]}</code>", t)

_LI = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")

def _md_list(items):
    out, stack = [], []
    for ind, mark, text in items:
        tag = "ol" if mark[0].isdigit() else "ul"
        while stack and ind < stack[-1][0]:
            out.append(f"</li></{stack.pop()[1]}>")
        if stack and ind == stack[-1][0] and stack[-1][1] != tag:  # bullet <-> numbered at the same level starts a new list
            out.append(f"</li></{stack.pop()[1]}>")
        if stack and ind == stack[-1][0]:
            out.append("</li>")
        else:
            stack.append((ind, tag)); out.append(f"<{tag}>")
        task = re.match(r"\[([ xX])\]\s+(.*)$", text)
        if task:
            out.append(f'<li class="task {"done" if task.group(1) != " " else ""}"><span class="cb">{"&#9745;" if task.group(1) != " " else "&#9744;"}</span> {md_inline(task.group(2))}')
        else:
            out.append("<li>" + md_inline(text))
    while stack:
        out.append(f"</li></{stack.pop()[1]}>")
    return "".join(out)

def md_to_html(text):
    """Small markdown renderer (headings, paragraphs, lists incl. tasks, fenced code, tables, quotes, rules, inline code/bold/italic/links). Output is escaped."""
    lines = (text or "").replace("\t", "    ").splitlines()
    out, i, para = [], 0, []
    def flush():
        if para:
            out.append("<p>" + md_inline(" ".join(x.strip() for x in para)) + "</p>"); para.clear()
    if lines and lines[0].strip() == "---":  # front matter
        j = next((k for k in range(1, min(len(lines), 60)) if lines[k].strip() == "---"), None)
        if j:
            out.append('<pre class="mdcode"><code>' + esc("\n".join(lines[1:j])) + "</code></pre>"); i = j + 1
    while i < len(lines):
        ln = lines[i]
        if ln.strip().startswith("```"):
            flush(); lang = ln.strip()[3:].strip(); buf = []; i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i]); i += 1
            out.append(f'<pre class="mdcode"><code>{esc(chr(10).join(buf))}</code></pre>'); i += 1; continue
        m = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", ln)
        if m:
            flush(); n = len(m.group(1)); out.append(f"<h{n}>{md_inline(m.group(2))}</h{n}>"); i += 1; continue
        if re.match(r"^\s*([-*_])(\s*\1){2,}\s*$", ln):
            flush(); out.append("<hr>"); i += 1; continue
        if "|" in ln and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$", lines[i + 1]):
            flush()
            cells = lambda r: [c.strip() for c in r.strip().strip("|").split("|")]
            head, i = cells(ln), i + 2
            rows = []
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                rows.append(cells(lines[i])); i += 1
            out.append("<table><thead><tr>" + "".join(f"<th>{md_inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{md_inline(c)}</td>" for c in r) + "</tr>" for r in rows) + "</tbody></table>")
            continue
        if ln.lstrip().startswith(">"):
            flush(); buf = []
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i])); i += 1
            out.append("<blockquote>" + md_to_html("\n".join(buf)) + "</blockquote>"); continue
        m = _LI.match(ln)
        if m:
            flush(); items = []
            while i < len(lines):
                m = _LI.match(lines[i])
                if m:
                    items.append([len(m.group(1)), m.group(2), m.group(3)]); i += 1
                elif lines[i].strip() and lines[i][:1] == " " and items:
                    items[-1][2] += " " + lines[i].strip(); i += 1
                elif not lines[i].strip() and i + 1 < len(lines) and _LI.match(lines[i + 1]):
                    i += 1
                else:
                    break
            out.append(_md_list(items)); continue
        if not ln.strip():
            flush()
        else:
            para.append(ln)
        i += 1
    flush()
    return "".join(out)

def md_block(text, empty="None recorded"):
    """Rendered markdown with a Rendered/Raw toggle."""
    if not text:
        return f'<span class="empty">{empty}</span>'
    return ('<div class="mdwrap"><div class="seg mdseg"><button type="button" data-mdv="r" class="on">Rendered</button><button type="button" data-mdv="raw">Raw</button></div>'
            f'<div class="md">{md_to_html(text)}</div><pre class="txt mdraw" hidden>{esc(text)}</pre></div>')

def rich(t):
    """Escape, then turn `code` into <code> and **bold** into <b>."""
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", esc(t))
    return re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)

def _bullets(v):
    items = v if isinstance(v, list) else [v]
    return "<ul>" + "".join(f"<li>{rich(i)}</li>" for i in items if i) + "</ul>"

def why_panel(items):
    """Explanation schema (all but title/why optional, keep each short):
    title (<=70 chars), why (1-2 sentences), points [short bullets], example (text block, e.g. input -> result),
    alternatives / risks (string or list)."""
    out = []
    for e in items:
        parts = [f'<h5>{rich(e.get("title", "Decision"))}</h5>']
        if e.get("why"):
            parts.append(f'<p class="lead">{rich(e["why"])}</p>')
        if e.get("points"):
            parts.append(f'<div class="wp">{_bullets(e["points"])}</div>')
        if e.get("example"):
            parts.append(f'<div class="wx"><span class="wl">Example</span><pre class="wex">{esc(e["example"])}</pre></div>')
        for k, lbl in (("alternatives", "Alternatives"), ("risks", "Risks &amp; tests")):
            if e.get(k):
                parts.append(f'<div class="wx"><span class="wl">{lbl}</span><div class="wt">{_bullets(e[k])}</div></div>')
        out.append(f'<div class="why">{"".join(parts)}</div>')
    return "".join(out)

def attach_explanations(f, ex):
    """Return (file_level, {hunk_index: [explanations]}) for this file; `match` picks the first hunk containing it."""
    hunks, cur = [], None
    for k, o, n, t in f["rows"]:
        if k == "hunk":
            cur = [t]; hunks.append(cur)
        elif cur is not None and t is not None:
            cur.append(t)
    by_hunk, file_level = {}, []
    for e in ex:
        m = e.get("match")
        hi = next((i for i, h in enumerate(hunks) if m and m in "\n".join(h)), None)
        if hi is None:
            if m: print(f"warning: explanation match not found in {f['path']}: {m!r}", file=sys.stderr)
            file_level.append(e)
        else:
            by_hunk.setdefault(hi, []).append(e)
    return file_level, by_hunk

def render_file(f, idx, rid, ex=(), ztests=None, mdsrc=None, tm=None):
    file_level, by_hunk = attach_explanations(f, ex)
    fid = f"{rid}-f{idx}"
    rows = _pairs(f["rows"])
    hn = -1
    ztests = dict(ztests or [])
    spec = bool(tm) and bool(ztests) and bool(re.search(tm["specPattern"], f["path"]))
    def zfor(raw):
        m = re.search(tm["testPattern"], html.unescape(raw)) if spec else None
        return (m.group(2), ztests.get(m.group(2))) if m and m.group(2) in ztests else None
    sign = {"add": "+", "del": "-"}
    u = []
    for k, o, n, t in rows:
        if k == "hunk":
            hn += 1
            ws = by_hunk.get(hn)
            if f["status"] in ("added", "deleted") and not ws:
                continue
            btn = f'<button type="button" class="whybtn" data-why="{fid}-h{hn}" aria-expanded="false">Why this change?</button>' if ws else ""
            u.append(f'<tr class="hunk"><td colspan="3"><div class="hh"><span>{t}</span>{btn}</div></td></tr>')
            if ws:
                u.append(f'<tr class="whyrow" hidden data-why="{fid}-h{hn}"><td colspan="3">{why_panel(ws)}</td></tr>')
        elif k == "meta":
            u.append(f'<tr class="meta"><td colspan="3">{t}</td></tr>')
        else:
            u.append(f'<tr class="{k}"><td class="n">{o or ""}</td><td class="n">{n or ""}</td><td class="c"><span class="sg">{sign.get(k, "&nbsp;")}</span>{t}</td></tr>')
            z = zfor(t) if k in ("add", "ctx") else None
            if z:
                u.append(zrow(z[0], z[1], f["path"], 3, tm))
    sp, i, hn = [], 0, -1
    while i < len(rows):
        k, o, n, t = rows[i]
        if k in ("hunk", "meta"):
            if k == "hunk":
                hn += 1
                ws = by_hunk.get(hn)
                if not (f["status"] in ("added", "deleted") and not ws):
                    btn = f'<button type="button" class="whybtn" data-why="{fid}-h{hn}" aria-expanded="false">Why this change?</button>' if ws else ""
                    sp.append(f'<tr class="hunk"><td colspan="4"><div class="hh"><span>{t}</span>{btn}</div></td></tr>')
                    if ws:
                        sp.append(f'<tr class="whyrow" hidden data-why="{fid}-h{hn}"><td colspan="4">{why_panel(ws)}</td></tr>')
            else:
                sp.append(f'<tr class="meta"><td colspan="4">{t}</td></tr>')
            i += 1
        elif k == "ctx":
            sp.append(f'<tr><td class="n">{o}</td><td class="c">{t}</td><td class="n">{n}</td><td class="c">{t}</td></tr>'); i += 1
            z = zfor(t)
            if z:
                sp.append(zrow(z[0], z[1], f["path"], 4, tm))
        else:
            dels, adds = [], []
            while i < len(rows) and rows[i][0] == "del": dels.append(rows[i]); i += 1
            while i < len(rows) and rows[i][0] == "add": adds.append(rows[i]); i += 1
            for x in range(max(len(dels), len(adds))):
                d = dels[x] if x < len(dels) else None
                a = adds[x] if x < len(adds) else None
                lc = f'<td class="n del">{d[1]}</td><td class="c del">{d[3]}</td>' if d else '<td class="n void"></td><td class="c void"></td>'
                rc = f'<td class="n add">{a[2]}</td><td class="c add">{a[3]}</td>' if a else '<td class="n void"></td><td class="c void"></td>'
                sp.append(f"<tr>{lc}{rc}</tr>")
                z = zfor(a[3]) if a else None
                if z:
                    sp.append(zrow(z[0], z[1], f["path"], 4, tm))
    changed = f["adds"] + f["dels"]
    spec_doc = f["path"].startswith("openspec/") or "/openspec/" in f["path"]  # openspec files always start collapsed
    big = spec_doc  # only openspec files start collapsed (click the header, or Expand all)
    d, _, name = f["path"].rpartition("/")
    label = {"added": "new", "deleted": "deleted", "renamed": "renamed"}.get(f["status"], "")
    badge = f'<span class="fbadge {f["status"]}">{label}</span>' if label else ""
    if f.get("dirty"):
        badge += f'<span class="fbadge unc" title="+{f["dirty"][0]} &minus;{f["dirty"][1]} not committed yet">uncommitted</span>'
    nwhy = len(file_level) + sum(len(v) for v in by_hunk.values())
    fbtn = f'<button type="button" class="whybtn fwhy" data-why="{fid}-file" aria-expanded="false">Why?</button>' if file_level else ""
    fpanel = f'<div class="whyfile" hidden data-why="{fid}-file">{why_panel(file_level)}</div>' if file_level else ""
    zb, zbar = "", ""
    if spec:
        total, done = len(ztests), sum(1 for v in ztests.values() if v)
        ok = done == total
        zb = f'<span class="zbadge {"ok" if ok else "warn"}" title="{done} of {total} automated tests published to {esc(tm["label"])}">{"&#10003;" if ok else "&#9888;"} {esc(tm["label"])} {done}/{total}</span>'
        zbar = (f'<div class="zfile {"ok" if ok else "warn"}"><span class="zi {"ok" if ok else "warn"}">{"&#10003;" if ok else "&#9888;"}</span>'
                f'<span><b>{esc(tm["label"])}</b> · {done} of {total} automated tests published{"" if ok else " — publish the rest to link executions"}</span><span class="zacts">'
                + ('' if ok else f'<button type="button" class="zbtn" data-zaction="tm-automation" data-file="{esc(f["path"])}">Publish all unpublished</button>')
                + '<button type="button" class="zbtn alt" data-zaction="tm-manual">Create manual test cases</button></span></div>')
    is_md = f["path"].lower().endswith(".md") and bool(mdsrc) and f["status"] != "deleted"
    prev_default = False  # markdown files open on the Diff view; Preview is one click away
    mdbar = ('<div class="mdbar"><div class="seg mdseg2"><button type="button" data-fv="diff">Diff</button><button type="button" data-fv="prev">Preview</button></div>'
             '<span class="sub">Preview renders the current file</span></div>'
             f'<div class="md mdprev">{md_to_html(mdsrc)}</div>') if is_md else ""
    body = zbar + fpanel + mdbar + (f'<div class="dv dv-u"><table class="dt">{"".join(u)}</table></div>'
            f'<div class="dv dv-s"><table class="dt st">{"".join(sp)}</table></div>') if rows else '<div class="empty pad">No textual changes</div>'
    return (f'<details class="file{" md-prev" if prev_default else ""}" id="{fid}" data-why-count="{nwhy}" data-path="{esc(f["path"].lower())}"{"" if big and not prev_default else " open"}>'
            f'<summary><span class="chev"></span><span class="fp"><span class="fd">{esc(d + "/" if d else "")}</span><b>{esc(name)}</b></span>{badge}{zb}'
            f'<span class="fstat"><span class="a">+{f["adds"]}</span> <span class="r">&minus;{f["dels"]}</span>{f"<span class=big>spec · {changed} lines · click to expand</span>" if big else ""}</span>{fbtn}</summary>{body}</details>')

def new_file_diff(rel, text):
    """A unified diff section that adds `text` as the new file `rel`."""
    body = text.splitlines()
    head = f"diff --git a/{rel} b/{rel}\nnew file\n--- /dev/null\n+++ b/{rel}\n"
    return head + (f"@@ -0,0 +1,{len(body)} @@\n" + "".join(f"+{x}\n" for x in body) if body else "")

def repo_diff(path, base):
    """(fork point, diff text): working copy vs where the branch left base (committed + uncommitted) plus brand-new untracked text files (<=200KB each)."""
    mb = vcs.out(path, "fork_point", base=base).strip() or base
    diff = vcs.out(path, "diff", rev=mb)
    for f in vcs.lines(path, "untracked"):
        fp = Path(path) / f
        try:
            raw = fp.read_bytes()
        except OSError:
            continue
        if len(raw) > 200_000 or b"\0" in raw[:4096]:
            continue
        diff += new_file_diff(f, raw.decode(errors="replace"))
    return mb, diff

def uncommitted_files(path):
    """{file: (adds, dels)} for work not yet committed: modified/staged/untracked files vs the last commit."""
    out = {f: (0, 0) for f in vcs.lines(path, "uncommitted")}
    for line in vcs.lines(path, "numstat"):
        a, d_, f = (line.split("\t") + ["", "", ""])[:3]
        f = f.split(" => ")[-1].strip("{}")
        if f in out and a.isdigit():
            out[f] = (int(a), int(d_))
    for f, v in out.items():
        if v == (0, 0):
            t = read_text(os.path.join(path, f))
            if t:
                out[f] = (t.count("\n") + 1, 0)
    return out

def snapshot(d):
    """{"<repo>/<file>": sha1 of that file's diff section}: what a report was generated from, to detect later outside changes."""
    snap = {}
    for r in d.get("repos", []):
        path = os.path.expanduser(r["path"])
        _, diff = repo_diff(path, base_branch(r))
        for f in re.split(r"(?m)^(?=diff --git )", diff):
            m = re.match(r"diff --git a/.* b/(.*)", f)
            if m:
                snap[f"{r['name']}/{m.group(1)}"] = hashlib.sha1(f.encode()).hexdigest()[:16]
    return snap

def snapshot_changes(d, old):
    """Files added, removed or edited since `old` snapshot: [(file, 'added'|'removed'|'modified')]."""
    new = snapshot(d)
    return ([(k, "added") for k in new if k not in old] + [(k, "removed") for k in old if k not in new]
            + [(k, "modified") for k in new if k in old and new[k] != old[k]])

def repo_section(r, explanations=(), tm=None):
    path, base = os.path.expanduser(r["path"]), base_branch(r)
    mb, diff = repo_diff(path, base)
    log = vcs.lines(path, "log", rev=mb)
    def commit_row(c):
        sha, _, msg = c.partition(" ")
        return f'<li class="cm"><i class="cd"></i><code class="sha">{esc(sha)}</code><span class="cmsg">{esc(msg)}</span></li>'
    commits = "".join(commit_row(c) for c in log)
    rid = "r" + re.sub(r"\W", "", r["name"])
    pf = sorted(parse_diff(diff), key=lambda f: tree_key(f["path"]))
    dirty = uncommitted_files(path)
    for f in pf:
        f["dirty"] = dirty.get(f["path"])
    nd = sum(1 for f in pf if f["dirty"])
    unc_row = ""
    if nd:
        da, dd = sum(f["dirty"][0] for f in pf if f["dirty"]), sum(f["dirty"][1] for f in pf if f["dirty"])
        unc_row = (f'<li class="cm unc"><i class="cd"></i><span class="uncpill">Uncommitted</span>'
                   f'<span class="cmsg">{nd} file{"s" if nd != 1 else ""} not committed yet</span>'
                   f'<span class="cstat"><span class="a">+{da}</span> <span class="r">&minus;{dd}</span></span></li>')
    commits = f'<ol class="timeline" aria-label="Commits">{unc_row}{commits}</ol>' if (unc_row or commits) else ""
    added, removed = sum(f["adds"] for f in pf), sum(f["dels"] for f in pf)
    zmap = {}
    for f in pf if tm else ():
        if re.search(tm["specPattern"], f["path"]):
            zt = tm_tests(read_text(os.path.join(path, f["path"])), tm)
            zmap[f["path"]] = zt
    zinfo = {k: (len(v), sum(1 for _, key in v if key)) for k, v in zmap.items()}
    mdmap = {f["path"]: read_text(os.path.join(path, f["path"])) for f in pf if f["path"].lower().endswith(".md")}
    html_ = tpl("repo.html").substitute(
        rid=rid, name=esc(r["name"]), branch=esc(r["branch"]), base=esc(base),
        pushed=("uncommitted changes" if nd else "pushed" if r.get("pushed") else "not pushed"), pushcls="ok" if r.get("pushed") and not nd else "warn",
        filecount=len(pf), added=added, removed=removed, addpct=f"{added * 100 / max(added + removed, 1):.1f}",
        commits=commits, tree=render_tree(pf, rid, zinfo, tm), files="".join(render_file(f, i, rid, [e for e in explanations if e.get("repo", r["name"]) == r["name"] and (f["path"] == e["file"] or f["path"].endswith("/" + e["file"]))], zmap.get(f["path"]), mdmap.get(f["path"]), tm) for i, f in enumerate(pf)) or '<div class="empty pad">No changes</div>')
    r["_dirty"] = nd
    return html_, len(pf), added, removed

def lst(items, empty):
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>" if items else f'<span class="empty">{empty}</span>'

def read_text(p, limit=200_000):
    try:
        t = Path(os.path.expanduser(p)).read_text(errors="replace")
        return t if len(t) <= limit else t[:limit] + "\n... (truncated)"
    except OSError:
        return None

def txt(t, empty="None recorded"):
    return f'<pre class="txt">{esc(t)}</pre>' if t else f'<span class="empty">{empty}</span>'

def agents_section(agents):
    return "".join(
        f'<details class="acc"><summary><span class="chev"></span><b>{esc(a.get("name", ""))}</b> <span class="pill">{esc(a.get("model", ""))}</span><span class="task">{esc(a.get("task", ""))}</span></summary>{md_block(a.get("result"), "No result recorded")}</details>'
        for a in agents) or '<div class="empty pad">None recorded</div>'

def artifacts_section(d):
    base = Path(os.path.expanduser(d.get("workspace", "")))
    out = []
    for a in d.get("artifacts", []):
        p = Path(os.path.expanduser(a))
        p = p if p.is_absolute() else base / a
        paths = sorted(f for f in p.rglob("*") if f.is_file()) if p.is_dir() else [p]
        out += [f'<details class="acc"><summary><span class="chev"></span><code>{esc(str(f).replace(str(base), "<workspace>"))}</code></summary>{md_block(read_text(f), "Unreadable") if str(f).lower().endswith(".md") else txt(read_text(f), "Unreadable")}</details>' for f in paths]
    return "".join(out) or '<div class="empty pad">None recorded</div>'

IMG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

def collect_evidence(d):
    """[(source Path, caption, test)] from d["evidence"]; when absent, every image in <workspace>/evidence/ (oldest first, caption from the file name)."""
    base = Path(os.path.expanduser(d.get("workspace", "")))
    items = []
    for e in d.get("evidence") or []:
        e = e if isinstance(e, dict) else {"file": e}
        p = Path(os.path.expanduser(e["file"]))
        p = p if p.is_absolute() else base / p
        if p.suffix.lower() in IMG_EXT and p.is_file():
            items.append((p, e.get("caption") or p.stem.replace("-", " ").replace("_", " "), e.get("test", "")))
    if not d.get("evidence"):
        ed = base / "evidence"
        if ed.is_dir():
            items = [(p, p.stem.replace("-", " ").replace("_", " "), "") for p in sorted(ed.iterdir(), key=lambda x: x.stat().st_mtime) if p.suffix.lower() in IMG_EXT]
    return items

def copy_evidence(d, out):
    """Snapshot evidence images next to the page (like diffs) so the report survives a deleted workspace; returns [(rel url, caption, test)]."""
    items, res, used = collect_evidence(d), [], set()
    if not items:
        return res
    ev = out / "evidence"
    ev.mkdir(parents=True, exist_ok=True)
    for src, cap, test in items:
        name = re.sub(r"[^A-Za-z0-9._-]", "_", src.name)
        while name in used:
            name = "x_" + name
        used.add(name)
        shutil.copyfile(src, ev / name)
        res.append((f"evidence/{name}", cap, test))
    return res

def evidence_section(evidence):
    if not evidence:
        return '<div class="empty pad">No screenshots recorded</div>'
    figs = "".join(
        f'<figure class="evf"><a class="evi" href="{esc(u)}" data-cap="{esc(c)}"><img loading="lazy" src="{esc(u)}" alt="{esc(c)}"></a>'
        f'<figcaption>{esc(c)}{f"<span class=evt>{esc(t)}</span>" if t else ""}</figcaption></figure>' for u, c, t in evidence)
    return f'<div class="evgrid">{figs}</div>'

def manual_md(mt):
    """Manual tests as plain text in the tracker's acceptance-criteria shape (see ../references/manual-tests-example.md)."""
    out = []
    if mt.get("intro"):
        out += [mt["intro"], ""]
    if mt.get("whatChanged"):
        out += ["WHAT CHANGED", mt["whatChanged"], ""]
    for n, t in enumerate(mt.get("tests", []), 1):
        tk = t.get("ticket") if t.get("ticket") and t["ticket"] not in t.get("title", "") else ""
        out += [f"**TEST {n}: {t.get('title', '')}" + (f" ({tk})" if tk else "") + "**", ""]
        steps = t.get("steps", [])
        out += [f"{i}. {x}" for i, x in enumerate(steps, 1)]
        k = len(steps)
        exp = t.get("expected", [])
        if len(exp) == 1:
            k += 1; out.append(f"{k}. Expected: {exp[0]}")
        elif exp:
            k += 1; out += [f"{k}. Expected:", ""] + [f"    * {e}" for e in exp] + [""]
        if t.get("before"):
            k += 1; out.append(f"{k}. Before the fix: {t['before']}")
        for note in t.get("notes", []):
            k += 1; out.append(f"{k}. {note}")
        out.append("")
    a = mt.get("automated")
    if a:
        out += ["**AUTOMATED COVERAGE**", a.get("text", "")]
        if a.get("command"):
            out.append(f"Run them with: {a['command']}")
        if a.get("setup"):
            out.append(a["setup"])
    return "\n".join(out).strip() + "\n"

ENV_WORDS = ["stage", "staging", "localhost", "targetEnv"]

def env_re(extra=()):
    words = "|".join(re.escape(w) for w in [*ENV_WORDS, *extra])
    return re.compile(rf"\b({words})\b|127\.0\.0\.1|:\d{{4,5}}\b|spring\.profiles|\bprofiles?\b", re.I)

def lint_manual(mt, extra=()):
    """Manual tests must not name an environment (environment names, hosts, ports, profiles, local-run flags): return the offending strings.
    `extra` adds project-specific environment names and hosts (the report's manualTestsForbid)."""
    bad, rx = [], env_re(extra)
    def walk(v):
        if isinstance(v, str):
            m = rx.search(v)
            if m:
                bad.append(f"{m.group(0)!r} in: {v[:90]}")
        elif isinstance(v, list):
            for x in v: walk(x)
        elif isinstance(v, dict):
            for x in v.values(): walk(x)
    walk(mt)
    return bad

def _t_html(n, t):
    tk = t.get("ticket") if t.get("ticket") and t["ticket"] not in t.get("title", "") else ""
    head = f"<p><b>TEST {n}: {rich(t.get('title', ''))}" + (f" ({esc(tk)})" if tk else "") + "</b></p>"
    items = [f"<li>{rich(x)}</li>" for x in t.get("steps", [])]
    exp = t.get("expected", [])
    if len(exp) == 1:
        items.append(f"<li>Expected: {rich(exp[0])}</li>")
    elif exp:
        items.append("<li>Expected:<ul>" + "".join(f"<li>{rich(e)}</li>" for e in exp) + "</ul></li>")
    if t.get("before"):
        items.append(f"<li>Before the fix: {rich(t['before'])}</li>")
    items += [f"<li>{rich(x)}</li>" for x in t.get("notes", [])]
    return head + "<ol>" + "".join(items) + "</ol>"

def manual_html(mt):
    """Clean HTML (no classes or styles) that pastes into a ticket editor as headings-free bold labels, numbered steps and nested bullets."""
    out = []
    if mt.get("intro"):
        out.append(f"<p>{rich(mt['intro'])}</p>")
    if mt.get("whatChanged"):
        out.append(f"<p><b>WHAT CHANGED</b><br>{rich(mt['whatChanged'])}</p>")
    out += [_t_html(n, t) for n, t in enumerate(mt.get("tests", []), 1)]
    a = mt.get("automated")
    if a:
        lines = [x for x in (rich(a.get("text", "")), ("Run them with: " + f"<code>{esc(a['command'])}</code>") if a.get("command") else "", rich(a.get("setup", ""))) if x]
        out.append("<p><b>AUTOMATED COVERAGE</b><br>" + "<br>".join(lines) + "</p>")
    return "".join(out)

def manual_data(mt):
    """JSON the page copies from: whole document and each test, as {html, text}."""
    one = lambda n, t: {"html": _t_html(n, t), "text": manual_md({"tests": [t]}).replace("TEST 1:", f"TEST {n}:", 1)}
    d = {"all": {"html": manual_html(mt), "text": manual_md(mt)}, "tests": [one(n, t) for n, t in enumerate(mt.get("tests", []), 1)]}
    return json.dumps(d).replace("</", "<\\/")

def manual_section(mt, ticket, forbid=()):
    if not mt or not mt.get("tests"):
        return '<div class="card"><div class="empty">No manual tests recorded yet. Press <b>Rerun</b> to generate them from the ticket and the current changes.</div></div>', "{}"
    head = ""
    bad = lint_manual(mt, forbid)
    if bad:
        for b in bad:
            print(f"warning: manual tests mention an environment: {b}", file=sys.stderr)
        head += '<div class="banner"><div><b>These manual tests name an environment.</b> They must read the same in any environment (no environment names, hosts, ports, profiles or local-run steps). Fix, then Rerun.<span class="fl">' + esc("; ".join(bad[:4])) + '</span></div></div>'
    if mt.get("intro") or mt.get("whatChanged"):
        head += '<div class="card mt-head">' +(f'<p class="lead">{rich(mt["intro"])}</p>' if mt.get("intro") else "")
        if mt.get("whatChanged"):
            head += f'<div class="wx"><span class="wl">What changed</span><div class="wt">{rich(mt["whatChanged"])}</div></div>'
        head += "</div>"
    cards = []
    for n, t in enumerate(mt["tests"], 1):
        steps = "".join(f'<li><label><input type="checkbox" class="mtck" data-k="{esc(ticket)}-{n}-{i}"><span>{rich(x)}</span></label></li>' for i, x in enumerate(t.get("steps", []), 1))
        exp = t.get("expected", [])
        exp_html = ('<div class="mt-exp"><span class="wl">Expected</span>' + ("<ul>" + "".join(f"<li>{rich(e)}</li>" for e in exp) + "</ul>")) + "</div>" if exp else ""
        extra = (f'<div class="mt-before"><span class="wl">Before the fix</span>{rich(t["before"])}</div>' if t.get("before") else "")
        extra += "".join(f'<div class="mt-note">{rich(x)}</div>' for x in t.get("notes", []))
        tk = f'<span class="pill">{esc(t["ticket"])}</span>' if t.get("ticket") and t["ticket"] not in t.get("title", "") else ""
        cards.append(f'<details class="card mtc" open><summary><span class="mtn">Test {n}</span><span class="mtt">{rich(t.get("title", ""))}</span>{tk}<span class="mtprog"></span><button type="button" class="mtone" data-n="{n - 1}" title="Copy this test as rich text">Copy</button></summary>'
                     f'<ol class="mt-steps">{steps}</ol>{exp_html}{extra}</details>')
    a = mt.get("automated")
    auto = ""
    if a:
        auto = ('<div class="card"><h2>Automated coverage</h2>' + (f'<p style="margin:0 0 8px">{rich(a["text"])}</p>' if a.get("text") else "")
                + (f'<pre class="tcmd">{esc(a["command"])}</pre>' if a.get("command") else "") + (f'<p class="sub" style="margin:8px 0 0">{rich(a["setup"])}</p>' if a.get("setup") else "") + "</div>")
    return head + "".join(cards) + auto, manual_data(mt)

def test_metrics(t):
    """Stat tiles (+ a pass/skip/fail bar) for a test row. Uses the row's explicit `metrics`
    [{"label","value","tone": ok|warn|bad|neutral}] or derives them from the summary text."""
    sm = t.get("summary") or ""
    num = lambda m: int(m.group(1).replace(",", "")) if m else None
    ms = t.get("metrics")
    added = t.get("added")  # new test cases this ticket added: shown as "(+N)" on Tests and Passed
    bar = ""
    if not ms:
        ms = []
        total = num(re.search(r"([\d,]+)\s+tests?\b", sm))
        fail = num(re.search(r"([\d,]+)\s+failures?\b", sm))
        err = num(re.search(r"([\d,]+)\s+errors?\b", sm))
        skip = num(re.search(r"([\d,]+)\s+skipped\b", sm))
        b = re.search(r"BUILD (SUCCESSFUL|FAILED)", sm)
        runs = re.search(r"(\d+)\s+of\s+(\d+)\s+runs?", sm)
        if b:
            ms.append({"label": "Build", "value": b[1].title(), "tone": "ok" if b[1] == "SUCCESSFUL" else "bad"})
        if total is not None:
            ms.append({"label": "Tests", "value": f"{total:,}", "tone": "neutral", "delta": added})
            bad = (fail or 0) + (err or 0)
            ms.append({"label": "Passed", "value": f"{total - bad - (skip or 0):,}", "tone": "ok", "delta": added if not bad else None})
            if fail is not None or err is not None:
                ms.append({"label": "Failed", "value": f"{bad:,}", "tone": "bad" if bad else "ok"})
            if skip is not None:
                ms.append({"label": "Skipped", "value": f"{skip:,}", "tone": "warn" if skip else "neutral"})
            if total:
                seg = [(total - bad - (skip or 0), "ok"), (skip or 0, "warn"), (bad, "bad")]
                bar = '<div class="mbar">' + "".join(f'<i class="{c}" style="width:{n * 100 / total:.2f}%" title="{n:,}"></i>' for n, c in seg if n) + "</div>"
        else:
            npass = num(re.search(r"([\d,]+)\s+(?:tests?\s+)?pass(?:ed|es)?\b", sm)) if not runs else None
            if npass is None and runs:
                npass = int(runs[1]); nall = int(runs[2])
            else:
                nall = None
            if npass is not None:
                nfail = fail if fail is not None else ((nall - npass) if nall is not None else 0)
                ms.append({"label": "Tests", "value": f"{npass + nfail + (skip or 0):,}", "tone": "neutral", "delta": added})
                ms.append({"label": "Passed", "value": f"{npass:,}", "tone": "ok", "delta": added if not nfail else None})
                ms.append({"label": "Failed", "value": f"{nfail:,}", "tone": "bad" if nfail else "ok"})
                if skip is not None:
                    ms.append({"label": "Skipped", "value": f"{skip:,}", "tone": "warn" if skip else "neutral"})
                tot = npass + nfail + (skip or 0)
                if tot:
                    seg = [(npass, "ok"), (skip or 0, "warn"), (nfail, "bad")]
                    bar = '<div class="mbar">' + "".join(f'<i class="{c}" style="width:{n * 100 / tot:.2f}%" title="{n:,}"></i>' for n, c in seg if n) + "</div>"
    if not ms:
        return ""
    tiles = "".join(f'<div class="mt {esc(m.get("tone", "neutral"))}"><b>{esc(m["value"])}{(" <small>(+" + str(m["delta"]) + ")</small>") if m.get("delta") else ""}</b><span>{esc(m["label"])}</span></div>' for m in ms)
    return f'<div class="mrow">{tiles}</div>{bar}'

def test_detail(t, evidence):
    """Row details: summary (1 line), optional points (bullets), command (code block), screenshot chip.
    Legacy rows with only a long `detail` string show the first sentence, the rest behind 'More'."""
    summary, points, rest = t.get("summary"), t.get("points") or [], ""
    if not summary:
        det = t.get("detail", "")
        m = re.match(r"(.{20,220}?[.;])\s+(.*)$", det, re.S)
        summary, rest = (m.group(1), m.group(2)) if m and len(det) > 240 else (det, "")
    tiles = test_metrics(t)
    out = tiles if tiles else f'<div class="ts">{rich(summary)}</div>'  # tiles replace the prose summary and bullets
    if points and not tiles:
        out += "<ul class=\"tp\">" + "".join(f"<li>{rich(x)}</li>" for x in points) + "</ul>"
    if t.get("command"):
        out += f'<pre class="tcmd">{esc(t["command"])}</pre>'
    if rest:
        out += f'<details class="tmore"><summary>More</summary><div>{rich(rest)}</div></details>'
    if t.get("stale"):
        out += f'<div class="tstale">&#9888; Not re-run{": " + rich(t["stale"]) if isinstance(t.get("stale"), str) else ""}. Result is from {esc(t["ranAt"]) if t.get("ranAt") else "an earlier run"}.</div>'
    elif t.get("ranAt"):
        out += f'<div class="tran">Last run {esc(t["ranAt"])}</div>'
    idx = [i for i, (_, _, test) in enumerate(evidence or []) if test and test == t.get("kind")]
    if idx:
        out += f'<button type="button" class="evchip" data-ev="{idx[0]}">&#9635; {len(idx)} screenshot{"s" if len(idx) != 1 else ""}</button>'
    return out

def build(d, token="", evidence=None):
    ticket = d["ticket"]
    spec = d.get("spec") or (read_text(d["specFile"]) if d.get("specFile") else None)
    msg = d.get("commitMessage")
    msg = "\n\n".join(f"[{k}]\n{v}" for k, v in msg.items()) if isinstance(msg, dict) else msg
    pushed = bool(d.get("repos")) and all(r.get("pushed") for r in d["repos"])
    link = f'<a href="{esc(d["url"])}" target="_blank" rel="noopener">Open ticket &#8599;</a>' if d.get("url") else ""
    tl = d.get("tests", [])
    ok = lambda t: t["status"].lower() in ("pass", "passed")
    n_ok, n_fail = sum(ok(t) for t in tl), sum(t["status"].lower() in ("fail", "failed") for t in tl)
    n_skip = len(tl) - n_ok - n_fail
    tests = "".join(tpl("test_row.html").substitute(
        kind=esc(t["kind"]), status=esc(t["status"]), detail=test_detail(t, evidence),
        cls={"pass": "pass", "passed": "pass", "skipped": "skip", "n/a": "skip"}.get(t["status"].lower(), "fail"))
        for t in tl) or '<tr><td colspan="3" class="empty">None recorded</td></tr>'
    rv = d.get("review", {})
    review = (f'<div class="kv"><span>Cycles <b>{esc(rv.get("cycles", 0))}</b></span><span>Outcome <b>{esc(rv.get("outcome", "n/a"))}</b></span></div>'
              + lst([esc(n) for n in rv.get("notes", [])], "No notes"))
    hl = d.get("hiccups", [])
    hiccups = "".join(tpl("hiccup.html").substitute(title=esc(h["title"]), detail=esc(h.get("detail", "")), resolution=esc(h.get("resolution", "n/a")),
                                                     rcls="bad" if h.get("resolution", "").lower().startswith("not resolved") else "ok")
                      for h in hl) or '<div class="empty pad">None. Smooth run.</div>'
    setup = lst([esc(s) for s in d.get("setup", [])], "None recorded")  # never include passwords/tokens
    tm = test_mgmt(d)
    parts = [repo_section(r, d.get("explanations", []), tm) for r in d.get("repos", [])]
    if any(r.get("_dirty") for r in d.get("repos", [])):
        pushed = False  # uncommitted work: show "Not pushed" and keep Commit & push enabled
    fc, ad, rm = sum(p[1] for p in parts), sum(p[2] for p in parts), sum(p[3] for p in parts)
    pend = d.get("pendingCommits", [])
    staged = ""
    if pend:
        items = "".join(f'<div class="si"><b>{esc(c["message"])}</b><div class="sub">{esc(c["repo"])} · {esc(", ".join(c["files"]))}</div></div>' for c in pend)
        staged = (f'<div class="staged"><button type="button" class="chip" id="stagedbtn" aria-expanded="false" title="Created as separate commits when you press Commit &amp; push">'
                  f'&#9679; {len(pend)} staged commit{"s" if len(pend) != 1 else ""}</button>'
                  f'<div class="pop" id="stagedpop" hidden><div class="poph">Staged, not yet committed</div>{items}<div class="sub pn">Commit &amp; push creates these first, then pushes.</div></div></div>')
    manual_html, manual_text = manual_section(d.get("manualTests"), ticket, d.get("manualTestsForbid") or ())
    crit = d.get("acceptanceCriteria", [])
    criteria = ("<ul class=\"checks\">" + "".join(f"<li>{esc(c)}</li>" for c in crit) + "</ul>") if crit else '<span class="empty">None recorded</span>'
    fups = d.get("followups", [])
    return tpl("page.html").substitute(
        ticket=esc(ticket), title=esc(d.get("title", "")), ticket_link=link,
        generated=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        workspace=esc(d.get("workspace", "")), summary=esc(d.get("summary", "")),
        repos="".join(p[0] for p in parts) or '<div class="empty pad">No repos</div>',
        tests=tests, review=review, hiccups=hiccups, setup=setup,
        followups=lst([esc(f) for f in fups], "None"),
        analysis=txt(d.get("analysis")), criteria=criteria,
        spec=md_block(spec), agents=agents_section(d.get("agents", [])), artifacts=artifacts_section(d),
        commit_message=txt(msg, "No commit message prepared"), commit_raw=esc(msg or ""),
        token=esc(token), ticket_id=esc(ticket),
        push_state="Pushed" if pushed and not pend else ("Staged commits" if pend else "Not pushed"), push_cls="ok" if pushed and not pend else "warn", push_disabled="disabled" if pushed and not pend else "", staged=staged,
        n_files=fc, n_add=ad, n_rm=rm, n_ok=n_ok, n_fail=n_fail, n_skip=n_skip, n_tests=len(tl),
        n_hiccups=len(hl), n_why=len(d.get("explanations", [])), evidence=evidence_section(evidence or []), n_evidence=len(evidence or []), manual=manual_html, manual_data=manual_text, n_manual=len((d.get("manualTests") or {}).get("tests", [])), n_follow=len(fups), n_agents=len(d.get("agents", [])),
        fail_cls="bad" if n_fail else "ok", review_outcome=esc(rv.get("outcome", "n/a")), n_repos=len(parts))

def free_port(start):
    for p in range(start, start + 50):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    raise SystemExit("no free port")

def update_index(root, d, generated):
    """Upsert this ticket into the registry and re-render the all-tickets index."""
    reg_file = root / "reports.json"
    reg = json.loads(reg_file.read_text()) if reg_file.exists() else {}
    tests = d.get("tests", [])
    reg[d["ticket"]] = {
        "ticket": d["ticket"], "title": d.get("title", ""), "url": d.get("url", ""),
        "summary": d.get("summary", ""), "generated": generated,
        "repos": [r["name"] for r in d.get("repos", [])],
        "pushed": all(r.get("pushed") for r in d.get("repos", [])) and bool(d.get("repos")),
        "passed": sum(1 for t in tests if t["status"].lower() in ("pass", "passed")),
        "failed": sum(1 for t in tests if t["status"].lower() in ("fail", "failed")),
        "hiccups": len(d.get("hiccups", [])),
    }
    reg_file.write_text(json.dumps(reg, indent=1))
    rows = "".join(tpl("index_row.html").substitute(
        ticket=esc(e["ticket"]), title=esc(e["title"]), generated=esc(e["generated"]),
        repos="".join(f'<span class="pill">{esc(r)}</span>' for r in e["repos"]),
        pushed="Pushed" if e["pushed"] else "Not pushed", pushcls="ok" if e["pushed"] else "warn",
        tests=(f'<span class="badge pass">{e["passed"]} passed</span>' + (f'<span class="badge fail">{e["failed"]} failed</span>' if e["failed"] else "")),
        hiccups=e["hiccups"], summary=esc(e["summary"][:200].rsplit(" ", 1)[0] + "…" if len(e["summary"]) > 200 else e["summary"]))
        for e in sorted(reg.values(), key=lambda e: e["generated"], reverse=True))
    (root / "index.html").write_text(tpl("index.html").substitute(rows=rows, count=len(reg)))

def ensure_token(root):
    state = root / "server.json"
    st = json.loads(state.read_text()) if state.exists() else {}
    if not st.get("token"):
        st["token"] = secrets.token_hex(16)
        state.write_text(json.dumps(st))
    return st["token"]

def render_ticket(data, root):
    """Write the ticket page + report.json copy and refresh the all-tickets index."""
    vcs.use(data)
    out = root / data["ticket"]
    out.mkdir(parents=True, exist_ok=True)
    generated = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    data["snapshot"] = snapshot(data)  # what this page was generated from; the page compares it with the working tree
    data["generatedAt"] = datetime.datetime.now().isoformat(timespec="seconds")
    (out / "index.html").write_text(build(data, ensure_token(root), copy_evidence(data, out)))
    (out / "report.json").write_text(json.dumps(data, indent=1))
    update_index(root, data, generated)

def listener_pid(port):
    r = subprocess.run(["lsof", "-ti", f"tcp:{port}", "-sTCP:LISTEN"], capture_output=True, text=True)
    return int(r.stdout.split()[0]) if r.stdout.split() else None

def ensure_server(root, start_port):
    """One server (server.py) for the whole report root; reuse it if running, replace older static servers."""
    state = root / "server.json"
    st = json.loads(state.read_text()) if state.exists() else {}
    port = st.get("port")
    if port:
        with socket.socket() as s:
            alive = s.connect_ex(("127.0.0.1", port)) == 0
        if alive and st.get("version") == SERVER_VERSION:
            return port
        pid = listener_pid(port) if alive else None
        cmd = subprocess.run(["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True).stdout if pid else ""
        if pid and ("http.server" in cmd or "server.py" in cmd):  # only our own report servers
            os.kill(pid, signal.SIGTERM)
            for _ in range(30):  # wait for the port to free up so the URL stays the same
                with socket.socket() as s2:
                    if s2.connect_ex(("127.0.0.1", port)) != 0:
                        break
                time.sleep(0.1)
    port = start_port  # reports are always served on one fixed port, so a proxy (reportUrl) can point at it
    if listener_pid(port):
        raise SystemExit(f"port {port} is in use by something that is not the report server; free it (reports always serve on {port})")
    subprocess.Popen([sys.executable, str(Path(__file__).parent / "server.py"), str(root), str(port)],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    st.update({"port": port, "version": SERVER_VERSION})
    state.write_text(json.dumps(st))
    return port

if __name__ == "__main__":
    args = sys.argv[1:]
    data = json.loads(Path(args[0]).read_text())
    root = Path(os.environ.get("ARBOR_REPORT_ROOT", "~/.arbor-reports")).expanduser()
    render_ticket(data, root)
    if "--no-serve" in args:
        print(root / "index.html"); sys.exit()
    port = ensure_server(root, int(args[args.index("--port") + 1]) if "--port" in args else 8766)
    print(f"index:  http://localhost:{port}/\nticket: http://localhost:{port}/{data['ticket']}/")
    if data.get("reportUrl"):
        print(f"proxy:  {report_url(data, port)}")
    if "--no-open" not in args:
        subprocess.run(["open", report_url(data, port)])
