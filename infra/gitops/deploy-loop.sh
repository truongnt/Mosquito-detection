#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/mosquito/Mosquito-detection}"
BRANCH="${BRANCH:-main}"
INTERVAL="${GITOPS_INTERVAL:-30}"

cd "$APP_DIR"

echo "[gitops] app_dir=$APP_DIR branch=$BRANCH interval=${INTERVAL}s"

while true; do
  set +e
  git fetch --all --prune
  fetch_status=$?
  set -e

  if [ "$fetch_status" -ne 0 ]; then
    echo "[gitops] git fetch failed (check SSH key / token). retry in ${INTERVAL}s"
    sleep "$INTERVAL"
    continue
  fi

  local_rev="$(git rev-parse HEAD)"
  remote_rev="$(git rev-parse "origin/${BRANCH}")"

  if [ "$local_rev" != "$remote_rev" ]; then
    echo "[gitops] update detected ${local_rev:0:7} -> ${remote_rev:0:7}"
    git reset --hard "origin/${BRANCH}"

    if [ ! -f .env ] && [ -f .env.example ]; then
      cp .env.example .env
      echo "[gitops] created .env from .env.example (please edit secrets)"
    fi

    docker compose up -d --build
    docker compose --profile train up -d --build || true
    docker compose --profile autodeploy up -d || true
    echo "[gitops] deploy done"
  fi

  sleep "$INTERVAL"
done

