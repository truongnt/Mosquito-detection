#!/usr/bin/env python3
"""
Download VecTech/JHU "novel-species-detection" model files (paper artifacts) and extract locally.

Upstream repo: https://github.com/vectech-dev/novel-species-detection
License note: The upstream repository is CC BY-NC 4.0 (NonCommercial). Ensure your use complies.
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
import zipfile
from pathlib import Path


DEFAULT_ZIP_URL = "https://novel-species-detection-paper.s3.us-east-2.amazonaws.com/CNN_model_files.zip"


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "MosquitoAI/1.0 (+https://github.com/truongnt/Mosquito-detection)",
            "Accept": "*/*",
        },
    )
    with urllib.request.urlopen(req) as r:
        dest.write_bytes(r.read())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_ZIP_URL)
    ap.add_argument("--out", default="ml/models/external/vectech")
    ap.add_argument("--zip", default="ml/models/external/vectech/CNN_model_files.zip")
    args = ap.parse_args()

    out_dir = Path(args.out).resolve()
    zip_path = Path(args.zip).resolve()

    print(f"Downloading: {args.url}")
    print(f"To: {zip_path}")
    try:
        download(args.url, zip_path)
    except Exception as exc:
        print(f"Download failed: {exc}", file=sys.stderr)
        return 2

    print(f"Extracting to: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(out_dir)

    pths = sorted(out_dir.rglob("*.pth"))
    print(f"Found {len(pths)} .pth files")
    for p in pths[:30]:
        print(f" - {p}")
    if len(pths) > 30:
        print(" ...")

    print("\nNext: pick a weights_path from the list above and register it in Admin → Config under key 'models'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

