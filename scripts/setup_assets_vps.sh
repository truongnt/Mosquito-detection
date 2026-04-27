#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> Download MosquitoDL into data/raw/mosquitodl"
python ml/scripts/01_download_data.py --raw-dir data/raw --mosquitodl

echo "==> Preprocess MosquitoDL into data/processed/mosquitodl"
python ml/scripts/02_preprocess.py --raw-dir data/raw/mosquitodl --out-dir data/processed/mosquitodl

echo "==> Download VecTech weights (paper artifacts) into ml/models/external/vectech"
python scripts/download_vectech_model.py --out ml/models/external/vectech --zip ml/models/external/vectech/CNN_model_files.zip

echo "==> Generate Admin Config JSON for enabling VecTech model"
python scripts/gen_vectech_models_config.py --weights-root ml/models/external/vectech > ml/models/external/vectech/models.config.json

echo ""
echo "Done."
echo "- Weights folder: ml/models/external/vectech"
echo "- Config JSON saved: ml/models/external/vectech/models.config.json"
echo ""
echo "Next:"
echo "1) Restart containers (so backend can read /app/models/external/...)"
echo "2) In Admin → Cấu hình, set key 'models' to the JSON in models.config.json"

