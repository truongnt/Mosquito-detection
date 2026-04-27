#!/usr/bin/env bash
set -euo pipefail

# Manual deploy on VPS:
# - pull latest code
# - build images locally on VPS
# - restart containers

cd /root/docker/Mosquito-detection

git pull --ff-only

docker compose build backend frontend
docker compose up -d --remove-orphans

docker compose ps

