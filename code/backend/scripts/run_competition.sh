#!/usr/bin/env bash
set -euo pipefail
umask 027

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
CODE_DIR="$(cd -- "$BACKEND_DIR/.." && pwd)"
ENV_FILE="${1:-$CODE_DIR/.env.competition}"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing competition env file: $ENV_FILE" >&2
  exit 2
fi

# A competition profile contains database/admin/model credentials. Refuse to
# source it when another local account can read or modify it.
if PERMISSIONS="$(stat -f '%Lp' "$ENV_FILE" 2>/dev/null)"; then
  :
elif PERMISSIONS="$(stat -c '%a' "$ENV_FILE" 2>/dev/null)"; then
  :
else
  echo "Unable to verify permissions for competition env file: $ENV_FILE" >&2
  exit 5
fi
PERMISSIONS="${PERMISSIONS: -3}"
if (( (8#$PERMISSIONS & 077) != 0 )); then
  echo "Competition env file must not be accessible by group/others (run: chmod 600 '$ENV_FILE')." >&2
  exit 5
fi

PYTHON_BIN="${PYTHON_BIN:-$CODE_DIR/.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Project Python is not executable: $PYTHON_BIN" >&2
  echo "Set PYTHON_BIN explicitly or create code/.venv." >&2
  exit 3
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

if [[ "${ENVIRONMENT:-}" != "production" ]]; then
  echo "Competition startup requires ENVIRONMENT=production." >&2
  exit 4
fi


if [[ "${BACKEND_WORKERS:-1}" != "1" ]]; then
  echo "Competition runtime requires BACKEND_WORKERS=1; in-process AI budgets are not shared across workers." >&2
  exit 6
fi

cd "$BACKEND_DIR"
# Parse the full application settings before binding a port. Pydantic rejects
# weak/placeholder credentials and unsafe production switches fail-closed.
"$PYTHON_BIN" -c 'from app.core.config import settings; assert settings.ENVIRONMENT == "production"'
exec "$PYTHON_BIN" -m uvicorn app.main:app \
  --host 127.0.0.1 \
  --port "${BACKEND_PORT:-8001}" \
  --workers "${BACKEND_WORKERS:-1}" \
  --timeout-keep-alive 10 \
  --limit-concurrency 64 \
  --backlog 128
