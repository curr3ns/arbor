#!/usr/bin/env bash
# Symlink all skills from this repo into ~/.claude

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"

link() {
  local src="$1" dst="$2"
  if [ -L "$dst" ] && [ "$(readlink "$dst")" = "$src" ]; then
    echo "  ok  $dst"
  else
    ln -sfn "$src" "$dst"
    echo "  →   $dst"
  fi
}

# Skills: symlink each skill directory
echo "Skills"
mkdir -p "$CLAUDE_DIR/skills"
for skill_dir in "$REPO_DIR/.claude/skills"/*/; do
  [ -d "$skill_dir" ] || continue
  name="$(basename "$skill_dir")"
  link "$skill_dir" "$CLAUDE_DIR/skills/$name"
done

# Prune symlinks we previously created for skills that no longer exist in this
# repo. Only touch dangling links that point into this repo's skills dir, so
# links owned by other sources are left alone.
skills_src="$REPO_DIR/.claude/skills"
for dst in "$CLAUDE_DIR/skills"/*; do
  [ -L "$dst" ] || continue
  case "$(readlink "$dst")" in
    "$skills_src"/*) [ -e "$dst" ] || { rm -f "$dst"; echo "  ✗   $dst (removed)"; } ;;
  esac
done

echo "Done."
