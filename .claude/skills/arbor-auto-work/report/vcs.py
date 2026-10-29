"""Version control for the report scripts, driven by a VCS mapping instead of a hard-coded tool.

The mapping is JSON at ~/.claude/arbor/providers/vcs/<name>.json (or a path), named by the report's "vcs" field.
Each command is a shell template run with `sh -c` in the repo; placeholders are shell-quoted. Contract per command:

  current_branch                 print the checked-out branch
  default_branch                 print the remote's default branch name
  fork_point {base}              print the revision where HEAD left the remote copy of {base}
  diff {rev}                     unified diff of the working copy (tracked files) against {rev}, with
                                 "diff --git a/<path> b/<path>" file headers
  untracked                      list untracked, non-ignored files, one per line
  uncommitted                    list every file that differs from the last commit (staged, unstaged, untracked)
  numstat                        "<adds>\\t<dels>\\t<path>" per tracked file that differs from the last commit
  log {rev}                      "<short id> <subject>" per commit from {rev} to HEAD, newest first
  changed_since {rev}            list files that differ between {rev} and the working copy
  file_differs {file}            exit 1 when {file} differs from the last commit, 0 when it does not
  file_committed {file}          exit 0 when {file} exists in the last commit
  stage_all / staged / unstage_all
  commit {msgfile}               commit what is staged with the message in {msgfile}
  commit_files {msgfile} {files} commit only {files}
  push {branch}                  push {branch} and set its upstream; never force

"deny_writes" lists command prefixes the headless Rerun job may not run (every VCS write).
"""
import json, os, shlex, subprocess
from pathlib import Path

ROOT = Path("~/.claude/arbor/providers/vcs").expanduser()
_mapping = None


def use(d):
    """Load the mapping the report names; every call below uses it."""
    global _mapping
    name = d.get("vcs")
    if not name:
        raise SystemExit('report.json has no "vcs": name the VCS mapping (see references/report.md)')
    p = Path(os.path.expanduser(name)) if "/" in name else ROOT / f"{name}.json"
    try:
        _mapping = json.loads(p.read_text())
    except (OSError, ValueError) as e:
        raise SystemExit(f"cannot read the VCS mapping {p}: {e}")
    return _mapping


def command(op, **args):
    tpl = (_mapping or {}).get("commands", {}).get(op)
    if not tpl:
        raise SystemExit(f"the VCS mapping has no '{op}' command")
    quoted = {k: " ".join(shlex.quote(str(x)) for x in v) if isinstance(v, (list, tuple)) else shlex.quote(str(v)) for k, v in args.items()}
    return tpl.format(**quoted)


def run(path, op, **args):
    """(exit code, stdout, stderr) of a mapping command in the repo at `path`."""
    p = subprocess.run(["sh", "-c", command(op, **args)], cwd=os.path.expanduser(path), capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def out(path, op, **args):
    """stdout of a mapping command, or "" when it fails."""
    code, stdout, _ = run(path, op, **args)
    return stdout if code == 0 else ""


def lines(path, op, **args):
    return [x for x in out(path, op, **args).splitlines() if x.strip()]


def deny_writes():
    return list((_mapping or {}).get("deny_writes", []))
