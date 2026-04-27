import argparse
import random
import shutil
from pathlib import Path


def _image_files(root: Path) -> list[Path]:
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    return [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in exts]


def _infer_label(path: Path, root: Path) -> str:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return "unknown"
    parts = list(rel.parts)
    if len(parts) >= 2:
        return parts[0].lower()
    return "unknown"


def preprocess_mosquitodl(
    raw_root: Path,
    out_root: Path,
    max_per_label: int,
    val_ratio: float,
    test_ratio: float,
    seed: int,
) -> dict:
    if not raw_root.exists():
        raise FileNotFoundError(f"Raw dataset not found: {raw_root}")

    files = _image_files(raw_root)
    if not files:
        hints = [
            f"No images found in {raw_root}",
            "Expected a folder structure like:",
            "  data/raw/mosquitodl/<label>/*.jpg",
            "If you cloned a dataset repo and it contains no images, you may need to download the dataset separately (or use Git LFS).",
        ]
        raise ValueError("\n".join(hints))

    by_label: dict[str, list[Path]] = {}
    for f in files:
        label = _infer_label(f, raw_root)
        by_label.setdefault(label, []).append(f)

    rng = random.Random(seed)
    if out_root.exists():
        shutil.rmtree(out_root)

    (out_root / "train").mkdir(parents=True, exist_ok=True)
    (out_root / "val").mkdir(parents=True, exist_ok=True)
    (out_root / "test").mkdir(parents=True, exist_ok=True)

    labels = sorted(by_label.keys())
    total_selected = 0
    total_copied = 0

    for label in labels:
        paths = by_label[label]
        rng.shuffle(paths)
        selected = paths[: max_per_label if max_per_label > 0 else len(paths)]
        total_selected += len(selected)

        n_test = int(len(selected) * test_ratio)
        n_val = int(len(selected) * val_ratio)
        n_train = max(0, len(selected) - n_test - n_val)

        splits = {
            "train": selected[:n_train],
            "val": selected[n_train : n_train + n_val],
            "test": selected[n_train + n_val : n_train + n_val + n_test],
        }

        for split_name, split_paths in splits.items():
            out_dir = out_root / split_name / label
            out_dir.mkdir(parents=True, exist_ok=True)
            for src in split_paths:
                shutil.copy2(src, out_dir / src.name)
                total_copied += 1

    return {
        "raw_root": str(raw_root),
        "processed_root": str(out_root),
        "labels": labels,
        "total_selected": total_selected,
        "total_copied": total_copied,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Preprocess MosquitoDL into YOLO classification folder structure")
    parser.add_argument("--raw-dir", default="data/raw/mosquitodl", help="Raw dataset path (MosquitoDL repo folder)")
    parser.add_argument("--out-dir", default="data/processed/mosquitodl", help="Output path")
    parser.add_argument("--max-per-label", type=int, default=500)
    parser.add_argument("--val-ratio", type=float, default=0.1)
    parser.add_argument("--test-ratio", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    res = preprocess_mosquitodl(
        raw_root=Path(args.raw_dir).resolve(),
        out_root=Path(args.out_dir).resolve(),
        max_per_label=args.max_per_label,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
        seed=args.seed,
    )
    print("✓ Preprocess done")
    print(res)


if __name__ == "__main__":
    main()
