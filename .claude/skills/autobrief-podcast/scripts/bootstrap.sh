#!/usr/bin/env bash
# AutoBrief podcast — environment bootstrap.
#
# Idempotent and safe to run on every pipeline start. It:
#   1. ensures the Python venv exists (creates it if missing)
#   2. installs any missing Python packages the pipeline needs
#   3. verifies system tools (ffmpeg/ffprobe)
#   4. verifies config (~/.claude/email_config.json)
#   5. verifies required API keys exist in the newsletter repo's .env
#
# Auto-fixes what's safe (venv, pip installs). Hard-fails with a clear
# message on things only a human can fix (missing API keys, ffmpeg, config).
#
# Usage:  bash scripts/bootstrap.sh
# Exit:   0 = ready, 1 = something needs manual attention.

set -uo pipefail

VENV="$HOME/.claude/email-venv"
PY="$VENV/bin/python"
PIP="$VENV/bin/pip"
CONFIG="$HOME/.claude/email_config.json"
NEWSLETTER_DEFAULT="$HOME/Code/02-ai-podcast-newsletter"

# package -> import-name (only list ones where they differ)
REQUIRED_PKGS=(anthropic elevenlabs httpx pydub python-dotenv requests)
import_name() {
  case "$1" in
    python-dotenv) echo "dotenv" ;;
    *) echo "$1" ;;
  esac
}

ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$1"; }
err()  { printf '  \033[31m✗\033[0m %s\n' "$1"; }

echo "AutoBrief bootstrap — checking environment…"
FATAL=0

# 1. python3
if ! command -v python3 >/dev/null 2>&1; then
  err "python3 not found on PATH"; FATAL=1
else
  ok "python3 $(python3 --version 2>&1 | awk '{print $2}')"
fi

# 2. venv
if [ ! -x "$PY" ]; then
  warn "venv missing — creating at $VENV"
  if python3 -m venv "$VENV"; then ok "created venv"; else err "failed to create venv"; exit 1; fi
else
  ok "venv present ($VENV)"
fi

# 3. python packages — import-check, install only what's missing
MISSING=()
for pkg in "${REQUIRED_PKGS[@]}"; do
  mod="$(import_name "$pkg")"
  "$PY" -c "import $mod" >/dev/null 2>&1 || MISSING+=("$pkg")
done
if [ "${#MISSING[@]}" -gt 0 ]; then
  warn "installing missing packages: ${MISSING[*]}"
  "$PIP" install --quiet --upgrade pip >/dev/null 2>&1
  if "$PIP" install --quiet "${MISSING[@]}"; then ok "installed: ${MISSING[*]}"; else err "pip install failed"; exit 1; fi
else
  ok "python packages present (${REQUIRED_PKGS[*]})"
fi

# 4. ffmpeg / ffprobe (needed for postprocess intro mix + image resizing)
for tool in ffmpeg ffprobe; do
  if command -v "$tool" >/dev/null 2>&1; then ok "$tool present"
  else err "$tool missing — install with: brew install ffmpeg"; FATAL=1; fi
done

# 5. email_config.json -> resolve newsletter dir
NEWSLETTER="$NEWSLETTER_DEFAULT"
if [ -f "$CONFIG" ]; then
  ok "email_config.json present"
  cfg_dir="$("$PY" -c "import json;print(json.load(open('$CONFIG')).get('podcast_dir',''))" 2>/dev/null)"
  [ -n "$cfg_dir" ] && NEWSLETTER="$cfg_dir"
else
  err "missing $CONFIG (needs \"account\" + \"podcast_dir\")"; FATAL=1
fi

# 6. .env with required API keys
ENV_FILE="$NEWSLETTER/.env"
REQUIRED_KEYS=(ELEVENLABS_API_KEY ANTHROPIC_API_KEY)
if [ -f "$ENV_FILE" ]; then
  ok ".env present ($ENV_FILE)"
  for key in "${REQUIRED_KEYS[@]}"; do
    if grep -qE "^${key}=.+" "$ENV_FILE"; then ok "$key set"
    else err "$key missing/empty in $ENV_FILE"; FATAL=1; fi
  done
else
  err "missing $ENV_FILE (needs ${REQUIRED_KEYS[*]})"; FATAL=1
fi

echo
if [ "$FATAL" -ne 0 ]; then
  err "bootstrap incomplete — fix the ✗ items above before running the pipeline."
  exit 1
fi
ok "environment ready."
