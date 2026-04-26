#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/root/docker/Mosquito-detection}"

cd "$APP_DIR"

if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
  echo "[deploy] created .env from .env.example (please edit secrets)"
fi

echo "[deploy] docker compose up --build"
docker compose up -d --build

if [ "${ENABLE_TRAIN_PROFILE:-0}" = "1" ]; then
  echo "[deploy] enabling train profile"
  docker compose --profile train up -d --build
fi

