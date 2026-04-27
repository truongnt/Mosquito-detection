#!/usr/bin/env bash
set -euo pipefail

cd /root/docker/Mosquito-detection

# 1) Get current git SHA (the version you want to deploy)
SHA="$(git rev-parse HEAD)"
echo "SHA=$SHA"

# 2) Pull backend image by SHA (avoid stale :main tag)
docker pull "ghcr.io/truongnt/mosquito-detection-backend:${SHA}"

# 3) Quick sanity check: ensure expected files exist in the image
docker run --rm "ghcr.io/truongnt/mosquito-detection-backend:${SHA}" sh -lc "ls -la /app/app/services | head -50"

# 4) Switch compose to SHA-pinned backend image (backup first)
cp docker-compose.yml docker-compose.yml.bak
sed -i "s|ghcr.io/truongnt/mosquito-detection-backend:main|ghcr.io/truongnt/mosquito-detection-backend:${SHA}|g" docker-compose.yml

# 5) Recreate backend/worker with the updated image
docker compose up -d --force-recreate backend worker

# 6) Confirm backend is running and check logs
docker inspect mosquito-detect-backend --format '{{.Image}}'
docker logs mosquito-detect-backend --tail 80

