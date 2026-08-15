#!/usr/bin/env bash
# store-ready installer
#
#   curl -fsSL https://raw.githubusercontent.com/USER/store-ready/main/install.sh | bash
#   ./install.sh --target claude-code|claude-project|cursor|gemini|agents|bundle
#
set -euo pipefail

REPO="${STORE_READY_REPO:-https://github.com/USER/store-ready.git}"
TARGET="${1:-}"
[[ "$TARGET" == --target ]] && TARGET="${2:-}"
TARGET="${TARGET#--target=}"

say() { printf '\033[1;34m›\033[0m %s\n' "$1"; }
die() { printf '\033[1;31m✗\033[0m %s\n' "$1" >&2; exit 1; }

command -v git >/dev/null || die "git is required"
command -v python3 >/dev/null || die "python3 is required"

if [[ -z "$TARGET" ]]; then
  cat <<'MENU'
Usage: install.sh --target <target>

  claude-code     ~/.claude/skills/store-ready        (Claude Code, all projects)
  claude-project  ./.claude/skills/store-ready        (this project only)
  cursor          ./.cursor/rules/ + ./AGENTS.md      (Cursor, Windsurf, Codex)
  gemini          ./GEMINI.md + ./store-ready/        (Gemini CLI)
  agents          ./AGENTS.md + ./store-ready/        (any AGENTS.md-aware agent)
  bundle          ./store-ready-prompt.md            (ChatGPT / Gemini web, paste)
MENU
  exit 0
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
say "Cloning $REPO"
git clone --depth 1 --quiet "$REPO" "$TMP/store-ready"
SRC="$TMP/store-ready"

install_to() {
  mkdir -p "$1"
  cp -R "$SRC/SKILL.md" "$SRC/AGENTS.md" "$SRC/references" "$SRC/scripts" "$1/"
  say "Installed to $1"
}

case "$TARGET" in
  claude-code)    install_to "$HOME/.claude/skills/store-ready" ;;
  claude-project) install_to "$PWD/.claude/skills/store-ready" ;;
  agents)
    install_to "$PWD/store-ready"
    cp "$SRC/AGENTS.md" "$PWD/AGENTS.md"
    say "Wrote ./AGENTS.md — adjust the paths inside to ./store-ready/"
    ;;
  cursor)
    install_to "$PWD/store-ready"
    mkdir -p "$PWD/.cursor/rules"
    cp "$SRC/AGENTS.md" "$PWD/.cursor/rules/store-ready.mdc"
    cp "$SRC/AGENTS.md" "$PWD/AGENTS.md"
    say "Wrote .cursor/rules/store-ready.mdc and ./AGENTS.md"
    ;;
  gemini)
    install_to "$PWD/store-ready"
    cp "$SRC/AGENTS.md" "$PWD/GEMINI.md"
    say "Wrote ./GEMINI.md"
    ;;
  bundle)
    python3 "$SRC/scripts/bundle.py" --out "dist/store-ready-prompt.md" >/dev/null
    cp "$SRC/dist/store-ready-prompt.md" "$PWD/store-ready-prompt.md"
    say "Wrote ./store-ready-prompt.md — paste it into a custom GPT or Gem"
    ;;
  *) die "unknown target: $TARGET" ;;
esac

say "Done. Try: python3 store-ready/scripts/preflight.py ."
