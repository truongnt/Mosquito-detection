#!/usr/bin/env python3
"""
Generate an Admin Config payload for enabling the VecTech novel-species-detection Xception model.

It expects you already downloaded/extracted weights under:
  ml/models/external/vectech/...

The resulting JSON should be pasted into Admin → Cấu hình under key "models".
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


FALLBACK_LABELS = [
    "aedes aedes_aegypti",
    "aedes aedes_albopictus",
    "aedes aedes_dorsalis",
    "aedes aedes_sollicitans",
    "aedes aedes_taeniorhynchus",
    "aedes aedes_vexans",
    "anopheles anopheles_coustani",
    "anopheles anopheles_freeborni",
    "anopheles anopheles_funestus",
    "anopheles anopheles_gambiae",
    "anopheles anopheles_punctipennis",
    "anopheles anopheles_quadrimaculatus",
    "culex culex_pipiens_sl",
    "culex culex_salinarius",
    "psorophora psorophora_columbiae",
    "psorophora psorophora_cyanescens",
    "aedes aedes_spp",
    "anopheles anopheles_spp",
    "culex culex_spp",
    "psorophora psorophora_spp",
    "mosquito",
]


def pick_weights(root: Path) -> Path:
    pths = sorted(root.rglob("*.pth"))
    if not pths:
        raise SystemExit(f"No .pth files found under {root}")

    def score(p: Path) -> tuple[int, int]:
        name = p.name.lower()
        # Prefer tier I closed-set weights if present.
        pri = 0
        if "closed" in name:
            pri += 10
        if "open" in name:
            pri += 5
        if "xception" in name:
            pri += 3
        return (pri, -len(name))

    return sorted(pths, key=score, reverse=True)[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights-root", default="ml/models/external/vectech")
    ap.add_argument("--model-id", default="vectech_xception")
    ap.add_argument("--name", default="VecTech Xception (paper)")
    ap.add_argument("--imsize", type=int, default=299)
    args = ap.parse_args()

    root = Path(args.weights_root).resolve()
    w = pick_weights(root)

    # Container path mapping: ./ml/models -> /app/models
    container_weights_path = str(Path("/app/models/external/vectech") / w.relative_to(root))

    payload = {
        "enabled": ["yolo", args.model_id],
        "registry": {
            args.model_id: {
                "name": args.name,
                "type": "vectech_xception",
                "description": "Xception weights from vectech-dev/novel-species-detection (paper artifacts).",
                "license": "CC BY-NC 4.0",
                "noncommercial_only": True,
                "weights_path": container_weights_path,
                "imsize": args.imsize,
                "labels": FALLBACK_LABELS,
            }
        },
    }

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

