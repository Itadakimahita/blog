#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

STEP=""
trap 'rc=$?; if [ $rc -ne 0 ]; then echo; echo "FAILED: ${STEP:-unknown step}"; exit $rc; fi' EXIT
trap 'echo; echo "Stopped."; exit 0' INT TERM

run_step() {
  STEP="$1"
  echo "==> $STEP"
  shift
  "$@"
}

trim() {
  local s="$1"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf '%s' "$s"
}

load_env_file() {
  local env_path="$1"
  while IFS= read -r line || [ -n "$line" ]; do
    line="$(trim "$line")"
    [ -z "$line" ] && continue
    [[ "$line" == \#* ]] && continue
    [[ "$line" != *=* ]] && continue

    local key="${line%%=*}"
    local val="${line#*=}"
    key="$(trim "$key")"
    val="$(trim "$val")"

    if [[ "$val" == \"*\" && "$val" == *\" ]]; then
      val="${val:1:${#val}-2}"
    elif [[ "$val" == \'*\' && "$val" == *\' ]]; then
      val="${val:1:${#val}-2}"
    fi

    [[ -n "$key" ]] && export "$key=$val"
  done < "$env_path"
}

run_step "Validate .env" bash -c '
  set -euo pipefail
  [ -f .env ] || { echo "Missing required file: .env"; exit 1; }

  required=(BLOG_ENV_ID)
  for k in "${required[@]}"; do
    v="$(grep -E "^[[:space:]]*${k}=" .env | head -n 1 | cut -d= -f2- || true)"
    v="${v#"${v%%[![:space:]]*}"}"; v="${v%"${v##*[![:space:]]}"}"
    if [ -z "$v" ]; then
      echo "Missing required environment variable: $k"
      exit 1
    fi
  done
'

run_step "Load .env" bash -c 'set -euo pipefail; :'
load_env_file ".env"

PYTHON_SYS="python3"
if ! command -v "$PYTHON_SYS" >/dev/null 2>&1; then
  PYTHON_SYS="python"
fi
if ! command -v "$PYTHON_SYS" >/dev/null 2>&1; then
  echo "Python is required (python3 or python not found)."
  exit 1
fi

VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
  run_step "Create virtual environment" "$PYTHON_SYS" -m venv "$VENV_DIR"
else
  echo "==> Create virtual environment (skipped; $VENV_DIR exists)"
fi

PY="$VENV_DIR/bin/python"
if [ -f "$VENV_DIR/Scripts/python.exe" ]; then
  PY="$VENV_DIR/Scripts/python.exe"
fi

run_step "Upgrade pip" "$PY" -m pip install --upgrade pip
run_step "Install dependencies" "$PY" -m pip install -r requirements/local.txt

run_step "Run migrations" "$PY" manage.py migrate --noinput
run_step "Collect static files" "$PY" manage.py collectstatic --noinput

run_step "Compile translations" "$PY" -c "
import os
from django.conf import settings
import django

env_id = os.environ.get('BLOG_ENV_ID')
if not env_id:
    raise SystemExit('BLOG_ENV_ID is required')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'settings.env.{env_id}')
django.setup()

from apps.abstracts.i18n_compile import compile_project_locales
compile_project_locales(list(getattr(settings, 'LOCALE_PATHS', [])))
print('Translations compiled')
"

ADMIN_EMAIL="admin@example.com"
ADMIN_PASSWORD="admin12345"
ADMIN_FIRST_NAME="Admin"
ADMIN_LAST_NAME="User"

run_step "Seed database + superuser (idempotent)" "$PY" manage.py seed_data \
  --admin-email "$ADMIN_EMAIL" \
  --admin-password "$ADMIN_PASSWORD" \
  --admin-first-name "$ADMIN_FIRST_NAME" \
  --admin-last-name "$ADMIN_LAST_NAME" \
  --update-admin-password
run_step "Start development server" bash -c "
  set -euo pipefail
  $PY manage.py runserver 0.0.0.0:8000 &
  server_pid=\$!

  for i in \$(seq 1 50); do
    if $PY -c \"import socket; s=socket.socket(); s.settimeout(0.2); s.connect(('127.0.0.1',8000)); s.close()\" >/dev/null 2>&1; then
      break
    fi
    sleep 0.2
  done

  echo
  echo \"Running development server at http://127.0.0.1:8000/\"
  echo \"API base:        http://127.0.0.1:8000/api/\"
  echo \"Swagger UI:      http://127.0.0.1:8000/api/docs/\"
  echo \"ReDoc:           http://127.0.0.1:8000/api/redoc/\"
  echo \"OpenAPI schema:  http://127.0.0.1:8000/api/schema/\"
  echo \"Admin:           http://127.0.0.1:8000/admin/\"
  echo
  echo \"Superuser:\"
  echo \"  Email:    $ADMIN_EMAIL\"
  echo \"  Password: $ADMIN_PASSWORD\"
  echo
  echo \"Press Ctrl+C to stop.\"
  echo

  wait \$server_pid
"