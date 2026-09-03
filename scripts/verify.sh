#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repository_root="$(cd "$script_dir/.." && pwd)"
cd "$repository_root"

notification_pycache="$(mktemp -d -t dcl-notification-pycache.XXXXXXXX)"
trap 'rm -rf -- "$notification_pycache"' EXIT

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=notifications/src \
  python3 -m unittest discover -s notifications/tests -v
PYTHONPYCACHEPREFIX="$notification_pycache" \
  python3 -m compileall -q notifications/src

npm --prefix frontend ci
npm --prefix frontend run lint
npm --prefix frontend run test
npm --prefix frontend run build
./backend/mvnw -f backend/pom.xml clean verify
npm --prefix frontend run test:e2e

