#!/usr/bin/env bash
# Verifies the Docker network segmentation described in
# docs/security/network-segmentation.md: only the proxy is reachable from the
# host, and the frontend cannot reach PostgreSQL directly (net_data is internal
# and the frontend never joins it). Run after `docker compose up -d`.
set -euo pipefail

fail=0

check() {
    local description="$1"
    shift
    if "$@"; then
        echo "PASS: $description"
    else
        echo "FAIL: $description"
        fail=1
    fi
}

check "proxy responds on host port 80" \
    curl -sk -o /dev/null -w '%{http_code}' http://localhost:80

check "proxy responds on host port 443" \
    curl -sk -o /dev/null -w '%{http_code}' https://localhost:443

check "frontend container cannot reach db:5432" \
    sh -c '! docker compose exec -T frontend sh -c "wget -q -T 2 -O- db:5432" >/dev/null 2>&1'

check "frontend container cannot reach minio:9000" \
    sh -c '! docker compose exec -T frontend sh -c "wget -q -T 2 -O- minio:9000" >/dev/null 2>&1'

check "backend container can reach db:5432" \
    docker compose exec -T backend sh -c "python -c \"import socket; socket.create_connection(('db', 5432), timeout=2)\""

for svc in db minio backend frontend proxy; do
    check "$svc container runs as non-root" \
        sh -c "[ \"\$(docker compose exec -T $svc id -u)\" != \"0\" ]"
done

exit "$fail"
