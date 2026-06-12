#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT/parking-backend"
API_DIR="$ROOT/parking-api"
APP_DIR="$ROOT/parking-app"
ANALYTICS_DIR="$ROOT/parking-analytics"
RUNTIME_DIR="$ROOT/.irs-runtime"

COMMAND="${1:-help}"
if [[ $# -gt 0 ]]; then
  shift
fi

VIDEO=""
MAX_FRAMES=0
ZONE_DWELL_SEC=-1
DB_HOST="localhost"
DB_PORT=5432
DB_ADMIN_USER="postgres"
DB_ADMIN_PASSWORD="1234"
NO_BACKEND=0

step() {
  printf '\n\033[36m==> %s\033[0m\n' "$1"
}

ok() {
  printf '\033[32m[OK] %s\033[0m\n' "$1"
}

warn() {
  printf '\033[33m[WARN] %s\033[0m\n' "$1"
}

die() {
  printf '\033[31m[ERROR] %s\033[0m\n' "$1" >&2
  exit 1
}

require_command() {
  local name="$1"
  local hint="$2"
  command -v "$name" >/dev/null 2>&1 || die "$name is not installed or not in PATH. $hint"
}

ensure_uv() {
  if command -v uv >/dev/null 2>&1; then
    ok "uv found: $(uv --version)"
    return
  fi

  step "Installing uv"
  require_command curl "Install Xcode Command Line Tools or curl."
  curl -LsSf https://astral.sh/uv/install.sh | sh

  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
  command -v uv >/dev/null 2>&1 || die "uv was installed but is still not available. Open a new terminal and run ./irs.sh install again."
  ok "uv installed: $(uv --version)"
}

run_in_dir() {
  local dir="$1"
  shift
  (cd "$dir" && "$@")
}

uv_in_dir() {
  local dir="$1"
  shift
  (cd "$dir" && UV_PROJECT_ENVIRONMENT=.venv-macos uv "$@")
}

port_pids() {
  local port="$1"
  lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null | sort -u || true
}

test_port() {
  [[ -n "$(port_pids "$1")" ]]
}

stop_port_listeners() {
  local ports=("$@")
  local port pid pids

  for port in "${ports[@]}"; do
    pids="$(port_pids "$port")"
    if [[ -z "$pids" ]]; then
      ok "Port $port is free"
      continue
    fi

    while IFS= read -r pid; do
      [[ -z "$pid" ]] && continue
      if [[ "$pid" == "$$" ]]; then
        warn "Skipping current launcher process on port $port"
        continue
      fi
      if kill "$pid" 2>/dev/null; then
        ok "Stopped PID $pid on port $port"
      else
        warn "Could not stop PID $pid on port $port"
      fi
    done <<< "$pids"
  done
}

wait_ports_free() {
  local deadline=$((SECONDS + 8))
  local busy=()
  while (( SECONDS < deadline )); do
    busy=()
    for port in "$@"; do
      test_port "$port" && busy+=("$port")
    done
    (( ${#busy[@]} == 0 )) && return
    sleep 0.3
  done

  busy=()
  for port in "$@"; do
    test_port "$port" && busy+=("$port")
  done
  (( ${#busy[@]} == 0 )) || die "Could not free app port(s): ${busy[*]}. Close those processes and try again."
}

stop_app_ports() {
  step "Stopping existing app processes on ports 8000, 3001, 5173"
  stop_pid_file "$RUNTIME_DIR/backend.pid"
  stop_pid_file "$RUNTIME_DIR/frontend.pid"
  stop_port_listeners 8000 3001 5173
  wait_ports_free 8000 3001 5173
}

stop_pid_file() {
  local file="$1"
  [[ -f "$file" ]] || return 0

  local pid
  pid="$(cat "$file" 2>/dev/null || true)"
  rm -f "$file"
  [[ -n "$pid" ]] || return 0

  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    ok "Stopped PID $pid from $(basename "$file")"
  fi
  return 0
}

start_background() {
  local name="$1"
  local dir="$2"
  local pid_file="$3"
  local log_file="$4"
  shift 4

  mkdir -p "$RUNTIME_DIR"
  : > "$log_file"
  nohup bash -c 'cd "$1" || exit 1; shift; exec "$@"' bash "$dir" "$@" >> "$log_file" 2>&1 &
  local pid
  pid=$!
  echo "$pid" > "$pid_file"
  ok "Started $name (PID $pid, log: $log_file)"
}

parse_options() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -MaxFrames|--max-frames)
        [[ $# -ge 2 ]] || die "$1 requires a value"
        MAX_FRAMES="$2"
        shift 2
        ;;
      -ZoneDwellSec|--zone-dwell-sec)
        [[ $# -ge 2 ]] || die "$1 requires a value"
        ZONE_DWELL_SEC="$2"
        shift 2
        ;;
      -DbHost|--db-host)
        [[ $# -ge 2 ]] || die "$1 requires a value"
        DB_HOST="$2"
        shift 2
        ;;
      -DbPort|--db-port)
        [[ $# -ge 2 ]] || die "$1 requires a value"
        DB_PORT="$2"
        shift 2
        ;;
      -DbAdminUser|--db-admin-user)
        [[ $# -ge 2 ]] || die "$1 requires a value"
        DB_ADMIN_USER="$2"
        shift 2
        ;;
      -DbAdminPassword|--db-admin-password)
        [[ $# -ge 2 ]] || die "$1 requires a value"
        DB_ADMIN_PASSWORD="$2"
        shift 2
        ;;
      -NoBackend|--no-backend)
        NO_BACKEND=1
        shift
        ;;
      -*)
        die "Unknown option: $1"
        ;;
      *)
        if [[ -z "$VIDEO" ]]; then
          VIDEO="$1"
        else
          die "Unexpected argument: $1"
        fi
        shift
        ;;
    esac
  done
}

show_help() {
  cat <<'EOF'
IRS Parking System macOS CLI

Usage:
  ./irs.sh install
  ./irs.sh init-db [--db-admin-password your-postgres-password]
  ./irs.sh start
  ./irs.sh stop
  ./irs.sh roi [video-file]
  ./irs.sh analytics [video-file]
  ./irs.sh headless [video-file] [--max-frames 300] [--zone-dwell-sec 0]
  ./irs.sh test
  ./irs.sh status

Windows-style flags are also accepted:
  -DbAdminPassword, -MaxFrames, -ZoneDwellSec, -NoBackend

Commands:
  install     Install Python/Node dependencies with uv and npm.
  init-db     Create expected PostgreSQL role/database and initialize tables.
  start       Stop old app listeners, then start backend + frontend/API in background.
  stop        Stop app listeners on ports 8000, 3001, 5173.
  roi         Open the parking zone drawing tool: parking-analytics/draw_roi.py.
  analytics   Run OpenCV GUI analytics: parking-analytics/main.py.
  headless    Run no-GUI analytics: parking-analytics/run_headless.py.
  test        Run analytics unit tests.
  status      Check ports 8000, 3001, 5173, 5432.

Default URLs:
  Frontend:    http://127.0.0.1:5173
  Express API: http://127.0.0.1:3001
  Backend:     http://127.0.0.1:8000
  PostgreSQL:  localhost:5432
EOF
}

install_all() {
  step "Checking required tools"
  require_command node "Install Node.js LTS, for example: brew install node"
  require_command npm "Install Node.js LTS, for example: brew install node"
  ensure_uv

  ok "node: $(node --version)"
  ok "npm: $(npm --version)"

  step "Installing Express API dependencies"
  run_in_dir "$API_DIR" npm install

  step "Installing frontend dependencies"
  run_in_dir "$APP_DIR" npm install

  step "Installing backend Python dependencies"
  uv_in_dir "$BACKEND_DIR" sync

  step "Installing analytics Python dependencies"
  uv_in_dir "$ANALYTICS_DIR" sync --dev

  ok "Install complete"
}

initialize_database() {
  parse_options "$@"
  step "Checking PostgreSQL"
  require_command psql "Install PostgreSQL, for example: brew install postgresql@16"

  local temp_sql
  temp_sql="$(mktemp)"
  cat > "$temp_sql" <<'SQL'
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'postgres') THEN
    CREATE ROLE postgres WITH LOGIN SUPERUSER PASSWORD '1234';
  ELSE
    ALTER ROLE postgres WITH LOGIN SUPERUSER PASSWORD '1234';
  END IF;
END
$$;

SELECT 'CREATE DATABASE parking_vkr OWNER postgres'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'parking_vkr')\gexec
SQL

  local old_pgpassword="${PGPASSWORD-}"
  export PGPASSWORD="$DB_ADMIN_PASSWORD"
  if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_ADMIN_USER" -d postgres -f "$temp_sql"; then
    rm -f "$temp_sql"
    if [[ -n "${old_pgpassword}" ]]; then
      export PGPASSWORD="$old_pgpassword"
    else
      unset PGPASSWORD
    fi
    die "psql failed. Make sure PostgreSQL is running and pass the installer password with: ./irs.sh init-db --db-admin-password <password>"
  fi
  rm -f "$temp_sql"
  if [[ -n "${old_pgpassword}" ]]; then
    export PGPASSWORD="$old_pgpassword"
  else
    unset PGPASSWORD
  fi

  step "Initializing backend tables"
  uv_in_dir "$BACKEND_DIR" run python database.py
  ok "Database initialized"
}

start_stack() {
  stop_app_ports
  ensure_uv

  step "Starting backend"
  start_background \
    "backend :8000" \
    "$BACKEND_DIR" \
    "$RUNTIME_DIR/backend.pid" \
    "$RUNTIME_DIR/backend.log" \
    env UV_PROJECT_ENVIRONMENT=.venv-macos uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000

  step "Starting frontend + Express API"
  start_background \
    "frontend :5173 + API :3001" \
    "$APP_DIR" \
    "$RUNTIME_DIR/frontend.pid" \
    "$RUNTIME_DIR/frontend.log" \
    npm run dev -- --host 127.0.0.1

  cat <<EOF

Started background services. Give them a few seconds, then open:
  http://127.0.0.1:5173

Health checks:
  http://127.0.0.1:8000/health
  http://127.0.0.1:3001/api/health

Logs:
  tail -f "$RUNTIME_DIR/backend.log"
  tail -f "$RUNTIME_DIR/frontend.log"
EOF
}

run_roi() {
  parse_options "$@"
  ensure_uv

  if [[ -n "$VIDEO" ]]; then
    uv_in_dir "$ANALYTICS_DIR" run python draw_roi.py "$VIDEO"
  else
    uv_in_dir "$ANALYTICS_DIR" run python draw_roi.py
  fi
}

run_analytics() {
  local headless="$1"
  shift
  parse_options "$@"
  ensure_uv

  export PARKING_BACKEND_ENABLED=1
  if [[ "$NO_BACKEND" == "1" ]]; then
    export PARKING_BACKEND_ENABLED=0
  fi
  export PARKING_BACKEND_URL="http://127.0.0.1:8000"
  if [[ "$ZONE_DWELL_SEC" -ge 0 ]]; then
    export ZONE_DWELL_SEC
  fi
  if [[ "$MAX_FRAMES" -gt 0 ]]; then
    export ANALYTICS_MAX_FRAMES="$MAX_FRAMES"
  fi

  local script="main.py"
  [[ "$headless" == "1" ]] && script="run_headless.py"

  if [[ -n "$VIDEO" ]]; then
    uv_in_dir "$ANALYTICS_DIR" run python "$script" "$VIDEO"
  else
    uv_in_dir "$ANALYTICS_DIR" run python "$script"
  fi
}

run_tests() {
  ensure_uv
  uv_in_dir "$ANALYTICS_DIR" run pytest -q
}

show_status() {
  local item port name state
  local rows=(
    "5432 PostgreSQL"
    "8000 FastAPI backend"
    "3001 Express API"
    "5173 Vue frontend"
  )

  for item in "${rows[@]}"; do
    port="${item%% *}"
    name="${item#* }"
    if test_port "$port"; then
      state="LISTENING"
    else
      state="not listening"
    fi
    printf '%-16s : %5s : %s\n' "$name" "$port" "$state"
  done
}

case "$COMMAND" in
  help|-h|--help) show_help ;;
  install) install_all "$@" ;;
  init-db) initialize_database "$@" ;;
  start) start_stack "$@" ;;
  stop) stop_app_ports "$@" ;;
  roi|draw-roi) run_roi "$@" ;;
  analytics) run_analytics 0 "$@" ;;
  headless) run_analytics 1 "$@" ;;
  test) run_tests "$@" ;;
  status) show_status "$@" ;;
  *) die "Unknown command: $COMMAND. Run ./irs.sh help." ;;
esac
