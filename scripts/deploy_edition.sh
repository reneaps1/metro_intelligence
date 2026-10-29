#!/usr/bin/env bash
# IQ-F9: build and start one edition on the VPS (docs/deployment-editions.md).
#
#   scripts/deploy_edition.sh metrology   # project metro-intelligence,            env .env
#   scripts/deploy_edition.sh industrial  # project metro-intelligence-industrial, env .env.industrial
#
# Run from the repository root on the VPS, after the code is at the wanted
# commit. The industrial edition is skipped (exit 0) while .env.industrial
# does not exist, so the workflow can deploy both before the second one is set up.
set -euo pipefail

edition="${1:-}"
case "$edition" in
  metrology) project="metro-intelligence"; env_file=".env" ;;
  industrial) project="metro-intelligence-industrial"; env_file=".env.industrial" ;;
  *) echo "usage: $0 metrology|industrial" >&2; exit 2 ;;
esac

if [[ ! -f "$env_file" ]]; then
  if [[ "$edition" == "industrial" ]]; then
    echo "SKIP industrial: $env_file not found (not configured on this host yet)."
    exit 0
  fi
  echo "ERROR: $env_file not found." >&2
  exit 1
fi

# The env file must declare the edition it deploys: a copied .env must never
# silently start a second metrology stack (or expose industrial routes).
declared="$(grep -E '^APP_EDITION=' "$env_file" | tail -n1 | cut -d= -f2- | tr -d '[:space:]"')"
if [[ "$declared" != "$edition" ]]; then
  echo "ERROR: $env_file declares APP_EDITION='$declared', expected '$edition'." >&2
  exit 1
fi
if [[ "$edition" == "industrial" ]] && ! grep -qE '^INSTANCE=' "$env_file"; then
  echo "ERROR: $env_file must set INSTANCE (volumes, data network and routers derive from it)." >&2
  exit 1
fi

compose=(docker compose -p "$project" --env-file "$env_file" -f docker-compose.vps.yml)
"${compose[@]}" config --quiet
"${compose[@]}" build frontend backend
if [[ "$edition" == "metrology" ]]; then
  # Leftovers from a manual `docker run` outside compose would block `up` with a name conflict.
  docker rm -f metro-intelligence-backend-1 metro-intelligence-frontend-1 2>/dev/null || true
fi
"${compose[@]}" up -d --remove-orphans

# Smoke test inside the container (independent of DNS/TLS): healthy, and
# running the edition this env file declares.
for _ in $(seq 1 30); do
  if "${compose[@]}" exec -T backend curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
    running="$("${compose[@]}" exec -T backend python -c 'from app.core.config import get_settings; print(get_settings().app_edition)')"
    if [[ "$(echo "$running" | tr -d '[:space:]')" != "$edition" ]]; then
      echo "ERROR: backend runs edition '$running', expected '$edition'." >&2
      exit 1
    fi
    echo "OK $edition deployed and healthy (project $project)."
    exit 0
  fi
  sleep 5
done
echo "ERROR: $edition backend not healthy after 150 s; see: ${compose[*]} logs backend" >&2
exit 1
