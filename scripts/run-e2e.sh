#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repository_root="$(cd "$script_dir/.." && pwd)"
cd "$repository_root"

postgres_image="postgres:17.10-alpine3.24"
postgres_name="dcl-e2e-postgres-$$-${RANDOM}"
database_name="dcl_e2e"
database_user="dcl_e2e"
database_password="dcl_e2e_only"
run_logs="$(mktemp -d -t dcl-e2e.XXXXXXXX)"
backend_pid=""
frontend_pid=""

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM

  if [[ -n "$frontend_pid" ]] && kill -0 "$frontend_pid" 2>/dev/null; then
    kill -- "-$frontend_pid" 2>/dev/null || true
    wait "$frontend_pid" 2>/dev/null || true
  fi

  if [[ -n "$backend_pid" ]] && kill -0 "$backend_pid" 2>/dev/null; then
    kill -- "-$backend_pid" 2>/dev/null || true
    wait "$backend_pid" 2>/dev/null || true
  fi

  docker rm --force "$postgres_name" >/dev/null 2>&1 || true

  if [[ "$run_logs" == /tmp/dcl-e2e.* ]]; then
    rm -rf -- "$run_logs"
  fi

  exit "$exit_code"
}
trap cleanup EXIT INT TERM

free_port() {
  node -e '
    const server = require("node:net").createServer();
    server.listen(0, "127.0.0.1", () => {
      console.log(server.address().port);
      server.close();
    });
  '
}

print_service_logs() {
  printf '%s\n' "Backend log:"
  tail -n 120 "$run_logs/backend.log" 2>/dev/null || true
  printf '%s\n' "Frontend log:"
  tail -n 120 "$run_logs/frontend.log" 2>/dev/null || true
}

docker info >/dev/null

docker run \
  --detach \
  --rm \
  --name "$postgres_name" \
  --publish 127.0.0.1::5432 \
  --env "POSTGRES_DB=$database_name" \
  --env "POSTGRES_USER=$database_user" \
  --env "POSTGRES_PASSWORD=$database_password" \
  "$postgres_image" >/dev/null

postgres_initialization_complete() {
  docker logs "$postgres_name" 2>&1 |
    grep --fixed-strings "PostgreSQL init process complete; ready for start up." >/dev/null
}

postgres_ready=false
for _ in {1..60}; do
  if postgres_initialization_complete && docker exec "$postgres_name" pg_isready --username "$database_user" --dbname "$database_name" >/dev/null 2>&1; then
    postgres_ready=true
    break
  fi
  sleep 1
done

if [[ "$postgres_ready" != true ]]; then
  printf '%s\n' "PostgreSQL did not become ready." >&2
  docker logs "$postgres_name" >&2 || true
  exit 1
fi

postgres_mapping="$(docker port "$postgres_name" 5432/tcp)"
postgres_port="${postgres_mapping##*:}"
backend_port="$(free_port)"
frontend_port="$(free_port)"

setsid env \
  SPRING_PROFILES_ACTIVE=local \
  SPRING_DATASOURCE_URL="jdbc:postgresql://127.0.0.1:${postgres_port}/${database_name}" \
  SPRING_DATASOURCE_USERNAME="$database_user" \
  SPRING_DATASOURCE_PASSWORD="$database_password" \
  SERVER_PORT="$backend_port" \
  ./backend/mvnw -f backend/pom.xml -DskipTests spring-boot:run \
  >"$run_logs/backend.log" 2>&1 &
backend_pid=$!

for _ in {1..120}; do
  if curl --fail --silent --show-error \
    "http://127.0.0.1:${backend_port}/actuator/health/readiness" >/dev/null 2>&1; then
    break
  fi
  if ! kill -0 "$backend_pid" 2>/dev/null; then
    print_service_logs >&2
    exit 1
  fi
  sleep 1
done

if ! curl --fail --silent --show-error \
  "http://127.0.0.1:${backend_port}/actuator/health/readiness" >/dev/null 2>&1; then
  printf '%s\n' "Backend did not become ready." >&2
  print_service_logs >&2
  exit 1
fi

setsid env \
  DCL_BACKEND_URL="http://127.0.0.1:${backend_port}" \
  npm --prefix frontend run dev -- --host 127.0.0.1 --port "$frontend_port" --strictPort \
  >"$run_logs/frontend.log" 2>&1 &
frontend_pid=$!

for _ in {1..60}; do
  if curl --fail --silent --show-error "http://127.0.0.1:${frontend_port}/" >/dev/null 2>&1; then
    break
  fi
  if ! kill -0 "$frontend_pid" 2>/dev/null; then
    print_service_logs >&2
    exit 1
  fi
  sleep 1
done

if ! curl --fail --silent --show-error "http://127.0.0.1:${frontend_port}/" >/dev/null 2>&1; then
  printf '%s\n' "Frontend did not become ready." >&2
  print_service_logs >&2
  exit 1
fi

if ! DCL_E2E_BASE_URL="http://127.0.0.1:${frontend_port}" \
  npm --prefix frontend exec -- playwright test --config frontend/playwright.config.ts; then
  print_service_logs >&2
  exit 1
fi

