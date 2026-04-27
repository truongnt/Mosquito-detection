#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

run_py() {
  if command -v python >/dev/null 2>&1; then
    python "$@"
    return 0
  fi

  if command -v python3 >/dev/null 2>&1; then
    python3 "$@"
    return 0
  fi

  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    # Use the worker image because it mounts ./ml and ./ml/models as writable.
    docker compose run --rm worker python "$@"
    return 0
  fi

  echo "ERROR: No python found on host, and docker compose is not available." >&2
  echo "Install python (python3) OR install Docker + Docker Compose and run from the repo root." >&2
  exit 1
}

echo "==> Download MosquitoDL into data/raw/mosquitodl"
run_py ml/scripts/01_download_data.py --raw-dir data/raw --mosquitodl

echo "==> Preprocess MosquitoDL into data/processed/mosquitodl"
run_py ml/scripts/02_preprocess.py --raw-dir data/raw/mosquitodl --out-dir data/processed/mosquitodl

echo "==> Download VecTech weights (paper artifacts) into ml/models/external/vectech"
run_py scripts/download_vectech_model.py --out ml/models/external/vectech --zip ml/models/external/vectech/CNN_model_files.zip

echo "==> Generate Admin Config JSON for enabling VecTech model"
run_py scripts/gen_vectech_models_config.py --weights-root ml/models/external/vectech --out ml/models/external/vectech/models.config.json

echo ""
echo "Done."
echo "- Weights folder: ml/models/external/vectech"
echo "- Config JSON saved: ml/models/external/vectech/models.config.json"
echo ""
echo "Next:"
echo "1) Restart containers (so backend can read /app/models/external/...)"
echo "2) In Admin → Cấu hình, set key 'models' to the JSON in models.config.json"

