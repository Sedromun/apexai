#!/usr/bin/env bash
# Build & (re)start the ApexAI production stack, then health-check it.
# Runs on the server (invoked by CI over SSH, or manually):
#   bash /opt/apexai/infra/deploy.sh
set -euo pipefail

cd "$(dirname "$0")/.."          # repo root, e.g. /opt/apexai
COMPOSE="docker compose -f infra/docker-compose.prod.yml --env-file .env"

echo "==> Building & starting stack"
$COMPOSE up -d --build --remove-orphans
docker image prune -f >/dev/null 2>&1 || true

DOMAIN="$(grep -E '^DOMAIN=' .env | cut -d= -f2)"
echo "==> Health-checking https://${DOMAIN}/papi/health"
healthy=0
for _ in $(seq 1 40); do
  if curl -skf --resolve "${DOMAIN}:443:127.0.0.1" "https://${DOMAIN}/papi/health" >/dev/null; then
    healthy=1
    echo "    backend healthy"
    break
  fi
  sleep 3
done
if [ "$healthy" -ne 1 ]; then
  echo "!! backend did not become healthy"
  $COMPOSE ps
  exit 1
fi
curl -skf --resolve "${DOMAIN}:443:127.0.0.1" "https://${DOMAIN}/" >/dev/null && echo "    web healthy"

$COMPOSE ps
echo "==> Deploy OK"
