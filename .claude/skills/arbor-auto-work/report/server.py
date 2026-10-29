#!/usr/bin/env python3
"""Local report server: serves the report root and runs the report page's action buttons.

Usage: server.py <root> <port>
Actions (POST /api/<TICKET>/<action>, poll GET /api/<TICKET>/jobs/<action>), all require the X-Report-Token header:
  commit-push        commit each repo with the report's commitMessage, then push the work branch (never forced)
  tm-automation      publish the automated specs added on the branch to the test-management system (only when the report
                     names a test-management mapping)
  tm-manual          draft manual test cases there from the report's manual tests (same condition)
  rerun              regenerate the report after outside changes: re-run tests, refresh explanations, manual tests and summary (headless claude)
Also GET /api/<TICKET>/status: files changed in the workspace since the report was generated.
Set ARBOR_REPORT_DRY_RUN=1 to log the test-management and rerun commands instead of running them.
"""
import json, os, re, subprocess, sys, threading, time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import build_report
import vcs

ROOT = Path(sys.argv[1]).resolve()
PORT = int(sys.argv[2])
SKILL = Path(__file__).resolve().parent.parent
ACTIONS = ("commit-push", "tm-automation", "tm-manual", "rerun")
PROTECTED = re.compile(r"^(development|main|master|release-.*)$")
SECRET = re.compile(r"(^|/)(\.env[^/]*|[^/]*\.(pem|key|p12|pfx)|id_rsa[^/]*|report\.json)$")
AI_LINE = re.compile(r"co-authored-by|generated with|claude|anthropic", re.I)
jobs, lock = {}, threading.Lock()


hist = {}  # ticket -> list of run entries (newest last); the live job objects are the same dicts


def history(ticket):
    """All runs for a ticket, loaded from <root>/<TICKET>/jobs.json once. Runs left 'running' by a dead server are marked failed."""
    if ticket not in hist:
        try:
            raw = json.loads((ROOT / ticket / "jobs.json").read_text())
        except (OSError, ValueError):
            raw = {}
        if isinstance(raw, dict) and isinstance(raw.get("history"), list):
            lst = raw["history"]
        else:  # legacy format: {action: job}
            lst = [{"id": f"legacy-{a}", "name": a, "label": "", "started": v.get("updated", 0), **v} for a, v in raw.items() if isinstance(v, dict)]
            lst.sort(key=lambda x: x.get("started", 0))
        for h in lst:
            if h.get("status") == "running":
                h["status"] = "failed"
                h["log"] = h.get("log", "") + "ERROR: interrupted (the report server restarted while this was running)\n"
        hist[ticket] = lst
    return hist[ticket]


def persist(ticket):
    """Write the run history to disk so logs survive reloads and server restarts. Caller holds lock."""
    (ROOT / ticket / "jobs.json").write_text(json.dumps({"history": history(ticket)[-100:]}))


def find_job(ticket, action):
    """'history' -> every run, newest first; 'last' -> newest run; otherwise the newest run of that action."""
    h = history(ticket)
    if action == "history":
        return {"history": list(reversed(h))}
    pick = [x for x in h if action == "last" or x.get("name") == action]
    return pick[-1] if pick else {"status": "idle", "log": ""}


def run_label(action, payload):
    payload = payload or {}
    if action == "rerun":
        return "re-run tests and regenerate explanations, manual tests and summary from the current code"
    if action == "commit-push":
        return "commit staged work and push the workspace branch"
    if action == "tm-manual":
        return "manual test cases from acceptance criteria"
    f = os.path.basename(payload.get("file", "")) or "all branch specs"
    return f + (": " + payload["title"] if payload.get("title") else " (all unpublished)")


def token():
    return json.loads((ROOT / "server.json").read_text()).get("token")


def load(ticket):
    d = json.loads((ROOT / ticket / "report.json").read_text())
    vcs.use(d)
    return d


def save(ticket, d):
    """Persist the report data (root copy + workspace copy) and re-render the page."""
    ws = Path(os.path.expanduser(d["workspace"])) / "report.json"
    if ws.parent.exists():
        ws.write_text(json.dumps(d, indent=2))
    build_report.render_ticket(d, ROOT)
    subprocess.run(["open", build_report.report_url(d, PORT)])  # show every re-rendered version


def vrun(path, log, op, **args):
    """Run a VCS mapping command, logging it like run()."""
    log("$ " + vcs.command(op, **args))
    code, stdout, stderr = vcs.run(path, op, **args)
    if (stdout + stderr).strip():
        log((stdout + stderr).strip())
    return code, stdout


def run(args, cwd, log, timeout=1800):
    log("$ " + " ".join(args if len(args) < 8 else args[:7] + ["..."]))
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    out = (p.stdout + p.stderr).strip()
    if out:
        log(out)
    return p.returncode, p.stdout


def commit_push(ticket, log):
    d = load(ticket)
    raw = d.get("commitMessage")
    if not raw and not d.get("pendingCommits"):
        raise RuntimeError("report has no commitMessage; generate it first (arbor-code-gencommit)")
    ws_file = Path(os.path.expanduser(d["workspace"])) / ".workspace.json"
    ws_branch = json.loads(ws_file.read_text())["branch"] if ws_file.exists() else None
    for r in d["repos"]:
        path, name = os.path.expanduser(r["path"]), r["name"]
        _, out = vrun(path, log, "current_branch")
        branch = out.strip()
        expected = ws_branch or r["branch"]
        if branch != expected or branch != r["branch"] or PROTECTED.match(branch):
            raise RuntimeError(f"{name}: on '{branch}', expected work branch '{expected}' (never push other/protected branches)")
        clean = lambda m: "\n".join(l for l in (m or "").splitlines() if not AI_LINE.search(l)).strip() + "\n"
        # staged commits first (e.g. test-management keys written into specs), each limited to its own files, so "add -A" below doesn't absorb them
        for i, pc in enumerate(p for p in d.get("pendingCommits", []) if p["repo"] == name):
            files = [f for f in pc["files"] if vrun(path, log, "file_differs", file=f)[0] == 1]
            if not files:
                log(f"{name}: staged commit '{pc['message']}' has no changes left, skipping")
                continue
            if [f for f in files if SECRET.search(f)]:
                raise RuntimeError(f"{name}: refusing to commit sensitive-looking files in staged commit")
            mf = ROOT / ticket / f"commit_msg_{name}_staged{i}.txt"
            mf.write_text(clean(pc["message"]))
            if vrun(path, log, "commit_files", msgfile=mf, files=files)[0]:
                raise RuntimeError(f"{name}: staged commit failed")
            log(f"{name}: committed '{pc['message']}'")
        msg = clean(raw.get(name) if isinstance(raw, dict) else raw) if raw else ""
        vrun(path, log, "stage_all") if raw else None
        _, staged = vrun(path, log, "staged") if raw else (0, "")
        bad = [f for f in staged.splitlines() if SECRET.search(f)]
        if bad:
            vrun(path, log, "unstage_all")
            raise RuntimeError(f"{name}: refusing to commit sensitive-looking files: {', '.join(bad)} (unstaged everything)")
        if staged.strip():
            mf = ROOT / ticket / f"commit_msg_{name}.txt"
            mf.write_text(msg)
            if vrun(path, log, "commit", msgfile=mf)[0]:
                raise RuntimeError(f"{name}: commit failed")
        else:
            log(f"{name}: nothing new to commit")
        if vrun(path, log, "push", branch=branch)[0]:
            raise RuntimeError(f"{name}: push failed")
        r["pushed"] = True
        d["pendingCommits"] = [p for p in d.get("pendingCommits", []) if p["repo"] != name]
        save(ticket, d)
    log("Done: pushed.")


def branch_specs(d, tm):
    specs = []
    for r in d["repos"]:
        path, base = os.path.expanduser(r["path"]), build_report.base_branch(r)
        mb = vcs.out(path, "fork_point", base=base).strip() or base
        changed, new = vcs.lines(path, "changed_since", rev=mb), vcs.lines(path, "untracked")
        for f in sorted(set(changed + new)):
            if re.search(tm["specPattern"], f):
                specs.append(f"{path}/{f}")
    return specs


def tm_job(ticket, kind, log, payload=None):
    d = load(ticket)
    tm = build_report.test_mgmt(d)
    if not tm or not tm.get("skill"):
        raise RuntimeError("no test-management mapping with a skill is named in this report (testManagement)")
    label, skill, env = tm["label"], tm["skill"], tm.get("tokenEnv", "")
    helper = os.path.expanduser(tm.get("helper", ""))
    example = build_report.tm_key(tm, "1234")
    rules = (f"Use the {skill} skill. Do not ask questions: infer what you can from the skill, and if something "
             "required is missing, report it instead of guessing. Reply with the created test case keys.\n")
    if env:
        rules += (f"Never print {env}. IMPORTANT: commands containing ${env} or `source ~/.zshrc` are blocked here. Do not use them. ")
    if helper:
        rules += (f"Make every {label} API call with this helper instead, which adds the base URL and auth: {helper} "
                  + (tm.get("helperUsage") or "METHOD /path ['json body']") + ". You may pipe its output to jq. "
                  "Use it wherever the skill shows a raw HTTP call.")
    payload = payload or {}
    if kind == "automation":
        specs = branch_specs(d, tm)
        if payload.get("file"):  # one spec file, only if it is a spec added on this branch
            specs = [x for x in specs if x.endswith("/" + payload["file"])]
        if not specs:
            raise RuntimeError("no automated spec files found on the branch")
        only = (f'Only the test titled "{payload["title"]}"; leave the other tests untouched.' if payload.get("title")
                else f"Only tests whose title has no key like {example} yet.")
        prompt = (f"{rules}\nCreate an automated {label} test case for tests in these spec files, then add each key to its "
                  f"test title in the form {example}. {only}\n" + "\n".join(specs))
    else:
        mt = d.get("manualTests") or {}
        if mt.get("tests"):
            body = build_report.manual_md(mt)
            prompt = (f"{rules}\nCreate one manual {label} test case per TEST block below for ticket {ticket} - {d.get('title', '')}: "
                      f"title = the TEST title, steps = the numbered actions, expected result = the Expected bullets (and the objective from the context):\n\n{body}")
        else:
            ac = "\n".join(f"- {a}" for a in d.get("acceptanceCriteria", [])) or d.get("summary", "")
            prompt = (f"{rules}\nCreate manual {label} test cases for ticket {ticket} - {d.get('title', '')}. "
                      f"Cover each acceptance criterion with clear steps and expected results:\n{ac}\nContext: {d.get('summary', '')}")
    # Skill: the system's skill; Edit: write keys into spec titles; helper/jq: API calls without a token in any command
    tools = ([f"Bash({helper}:*)"] if helper else []) + ["Bash(jq:*)", "Read", "Edit", "Glob", "Grep", "Skill"]
    cmd = 'claude -p "$0" --allowedTools "' + ",".join(tools) + '"'
    if os.environ.get("ARBOR_REPORT_DRY_RUN"):
        log("DRY RUN: " + cmd + "\n" + prompt)
        return
    if env and run(["zsh", "-ic", f'test -n "${env}"'], None, lambda s: None)[0]:
        raise RuntimeError(f"{env} is not set in ~/.zshrc (the {skill} skill needs it)")
    before = spec_keys(specs, tm) if kind == "automation" else {}
    # interactive zsh so the token from ~/.zshrc is available to the helper
    code, _ = run(["zsh", "-ic", cmd, prompt], os.path.expanduser(d["workspace"]), log)
    if code:
        raise RuntimeError(f"{label} run exited with code {code}")
    if kind == "automation":
        after = spec_keys(specs, tm)
        new = {f: sorted(after[f] - before[f]) for f in after if after[f] - before[f]}
        if not new:  # claude -p exits 0 even when the skill could not do its job
            raise RuntimeError("the run finished but no new key was written to any spec; see the output above for why")
        log("Linked: " + ", ".join(build_report.tm_key(tm, k) for ks in new.values() for k in ks))
        stage_commits(ticket, d, new, log, tm)


def spec_keys(specs, tm):
    """{spec path: set of test-management keys present in its test titles}."""
    out = {}
    for f in specs:
        try:
            out[f] = {k for _, k in build_report.tm_tests(Path(f).read_text(errors="replace"), tm) if k}
        except OSError:
            out[f] = set()
    return out


def stage_commits(ticket, d, new, log, tm):
    """Record a pending commit for committed specs that now differ from the last commit only because of new test-management keys.

    Nothing is committed here: Commit & push creates these commits (one per repo, only their files), then pushes.
    A spec that is still uncommitted needs no separate commit; it goes with the main one."""
    pend = d.setdefault("pendingCommits", [])
    for r in d["repos"]:
        path = os.path.expanduser(r["path"])
        files, keys = [], set()
        for spec, ks in new.items():
            if not spec.startswith(path + "/"):
                continue
            rel = spec[len(path) + 1:]
            in_head = vcs.run(path, "file_committed", file=rel)[0] == 0
            changed = vcs.run(path, "file_differs", file=rel)[0] == 1
            if in_head and changed:
                files.append(rel); keys.update(ks)
        if not files:
            continue
        old = next((p for p in pend if p["repo"] == r["name"]), None)
        if old:
            pend.remove(old); files = sorted(set(old["files"]) | set(files)); keys |= set(old["keys"])
        pend.append({"repo": r["name"], "files": files, "keys": sorted(keys),
                     "message": f"{ticket} Link automation tests to {tm['label']} ({', '.join(build_report.tm_key(tm, k) for k in sorted(keys))})"})
        log(f"{r['name']}: staged commit '{pend[-1]['message']}' (created on Commit & push)")
    save(ticket, d)




def rerun(ticket, log):
    """Headless claude run that refreshes the whole report after changes made outside the original process."""
    d = load(ticket)
    ws = Path(os.path.expanduser(d["workspace"]))
    old = d.get("snapshot") or {}
    changed = build_report.snapshot_changes(d, old) if old else []
    stamp = time.strftime("%Y%m%d-%H%M%S")
    (ROOT / ticket / f"report.json.bak-{stamp}").write_text((ROOT / ticket / "report.json").read_text())
    save(ticket, d)  # workspace copy = current report, so the agent edits the latest
    clist = "\n".join(f"- {f} ({k})" for f, k in changed) or "- none detected by the snapshot (still do every step; the snapshot may be missing)"
    base = build_report.base_branch(d["repos"][0]) if d.get("repos") else "main"
    vmap = f"~/.claude/arbor/providers/vcs/{d.get('vcs', '<name>')}.md"
    profile = f", the project profile {d['profile']} (its environment, test-data and manual-test rules apply)" if d.get("profile") else ""
    prompt = f"""You are re-running the implementation report for ticket {ticket} after changes were made outside the original process. Workspace: {ws}. The report data file is {ws}/report.json: edit ONLY that file (keep every key you do not change, including snapshot, generatedAt, pendingCommits, evidence, repos, commitMessage) and never print or store passwords or tokens. Never stage, commit, push, reset, switch branches, stash or clean with the VCS; the user commits from the report page. Do not ask questions; if something cannot be done, record exactly why in the report and continue.

Files changed since the report was generated:
{clist}

Steps, in order:
1. Read {ws}/report.json, {ws}/spec.md, {SKILL}/references/report.md (the report schema and the style rules for summary, tests, explanations, manualTests, evidence), {SKILL}/references/verification.md, {SKILL}/references/manual-tests-example.md{profile}. Look at each repo's current diff against {base} (plus untracked files) using the VCS mapping {vmap}.
2. Re-run tests. For every `tests` row that has a `command`, run that command from the right directory (the repo root, or the automation suite's directory for automation commands; keep any environment flags the command already carries) and update the row: `status` (passed/failed), one-line `summary`, short `points`, keep `command`, set `ranAt` to now (YYYY-MM-DD HH:MM, local time) and remove any `stale` key. If a command needs a service that is not running, start it using the profile's recipes when that is quick; otherwise mark the row `"stale": "<why>"` and keep its old result. For rows without a `command` (API checks, Browser checks that need enrolled users or a browser session) do not guess: set `"stale": "<short reason, e.g. needs browser and enrolled users>"` and keep the old status. If the changes added tests or code that no row covers, add a row with its command. If a re-run fails, say so honestly (status failed, summary naming the failure) and add a `hiccups` entry; do not fix source code.
3. Update `summary` and `analysis` only where the changes alter what was done. Keep `acceptanceCriteria` unless the changes make a criterion wrong.
4. Fix `explanations`: write or correct entries for every changed or new file and hunk (follow the explanation style rules in references/report.md: short `why`, bullets, example, `match` strings that occur in exactly one hunk); drop entries for files no longer in the diff; leave entries for untouched files as they are.
5. Regenerate `manualTests` (schema and house style in references/report.md and references/manual-tests-example.md) so the steps match the current behavior and test data approach (fresh test data, never ids from the ticket text). They must NOT name any environment, hostname, port, profile or local-run step (nor anything in the report's manualTestsForbid): write them so they read the same in any environment; put such details in `setup` instead.
6. Add `followups` or `hiccups` for anything left open. Validate that {ws}/report.json is valid JSON (`python3 -c "import json;json.load(open('{ws}/report.json'))"`) and stop.
Final reply, under 10 lines: what changed, which test rows were re-run and their results, which rows are stale and why."""
    deny = ",".join(f"Bash({c}:*)" for c in [*vcs.deny_writes(), "rm -rf"])
    cmd = 'claude -p "$0" --allowedTools "Bash,Read,Edit,Write,Glob,Grep,Skill" --disallowedTools "' + deny + '"'
    if os.environ.get("ARBOR_REPORT_DRY_RUN"):
        log("DRY RUN: " + cmd + "\n" + prompt)
        return
    code, _ = run(["zsh", "-ic", cmd, prompt], str(ws), log, timeout=3600)
    try:
        new = json.loads((ws / "report.json").read_text())
        assert new.get("ticket") == ticket
    except Exception as e:
        (ROOT / ticket / "report.json").write_text((ROOT / ticket / f"report.json.bak-{stamp}").read_text())
        raise RuntimeError(f"the rerun left an invalid report.json ({e}); the previous report was restored")
    if code:
        log(f"warning: claude exited with code {code}; using the report as it was left")
    save(ticket, new)
    log("Report regenerated.")


def start(ticket, action, payload=None):
    key = (ticket, action)
    with lock:
        if jobs.get(key, {}).get("status") == "running":
            return
        now = time.time()
        job = {"id": f"{int(now * 1000)}-{action}", "name": action, "label": run_label(action, payload), "status": "running",
               "log": "", "started": now, "updated": now}
        jobs[key] = job
        history(ticket).append(job)
        persist(ticket)

    def log(s):
        with lock:
            job["log"] += s + "\n"
            job["updated"] = time.time()

    def work():
        try:
            if action == "commit-push":
                commit_push(ticket, log)
            elif action == "rerun":
                rerun(ticket, log)
            else:
                tm_job(ticket, action.split("-")[1], log, payload)
            build_report.render_ticket(load(ticket), ROOT)  # refresh badges, staged commits, pushed state
            status = "done"
        except Exception as e:
            log(f"ERROR: {e}")
            status = "failed"
        with lock:
            job["status"] = status
            job["updated"] = time.time()
            job["log"] = job["log"][-200_000:]
            persist(ticket)

    threading.Thread(target=work, daemon=True).start()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(ROOT), **k)

    def log_message(self, *a):
        pass

    def reply(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def host_ok(self):
        return self.headers.get("Host", "") in (f"localhost:{PORT}", f"127.0.0.1:{PORT}")

    def authed(self):
        return self.host_ok() and self.headers.get("X-Report-Token") == token()

    def do_GET(self):
        ms = re.fullmatch(r"/api/([A-Za-z0-9-]+)/status", self.path)
        if ms and (ROOT / ms[1] / "report.json").exists():
            if not self.authed():
                return self.reply(403, {"error": "forbidden"})
            d = load(ms[1])
            old = d.get("snapshot")
            ch = build_report.snapshot_changes(d, old) if old else []
            return self.reply(200, {"changed": [{"file": f, "kind": k} for f, k in ch], "generatedAt": d.get("generatedAt", ""), "tracked": bool(old)})
        m = re.fullmatch(r"/api/([A-Za-z0-9-]+)/jobs/([a-z-]+)", self.path)
        if m:
            if not self.authed():
                return self.reply(403, {"error": "forbidden"})
            with lock:
                return self.reply(200, find_job(m[1], m[2]))
        if not self.host_ok():
            return self.reply(403, {"error": "forbidden"})
        super().do_GET()

    def do_POST(self):
        m = re.fullmatch(r"/api/([A-Za-z0-9-]+)/([a-z-]+)", self.path)
        if not m or m[2] not in ACTIONS or not (ROOT / m[1] / "report.json").exists():
            return self.reply(404, {"error": "unknown action"})
        if not self.authed():
            return self.reply(403, {"error": "forbidden"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(min(n, 65536)) or b"{}") if n else {}
        except ValueError:
            return self.reply(400, {"error": "bad body"})
        if not isinstance(payload, dict):
            return self.reply(400, {"error": "bad body"})
        start(m[1], m[2], {k: str(v)[:500] for k, v in payload.items() if k in ("file", "title")})
        self.reply(202, {"status": "running"})


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
