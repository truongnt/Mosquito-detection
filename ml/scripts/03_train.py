import argparse
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Ultralytics YOLO classification model (CPU by default)")
    parser.add_argument("--data", default="data/processed/mosquitodl", help="Processed dataset root (has train/val/test folders)")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--imgsz", type=int, default=224)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--lr0", type=float, default=0.001)
    parser.add_argument("--base-model", default="yolo26n-cls.pt", help="Base weights (e.g. yolo26n-cls.pt)")
    parser.add_argument("--out-dir", default="ml/models/saved", help="Where to copy best weights")
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    from ultralytics import YOLO

    data_root = Path(args.data).resolve()
    if not (data_root / "train").exists():
        raise SystemExit(f"Missing train folder in {data_root}")

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    model = YOLO(args.base_model)
    project = out_dir.parent / "runs"
    name = f"local_{data_root.name}"

    model.train(
        data=str(data_root),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        lr0=args.lr0,
        device=args.device,
        project=str(project),
        name=name,
        exist_ok=True,
        verbose=True,
    )

    best = project / name / "weights" / "best.pt"
    last = project / name / "weights" / "last.pt"
    src = best if best.exists() else last if last.exists() else None
    if not src:
        raise SystemExit(f"No weights found under {project/name/'weights'}")

    dst = out_dir / "best_model.pt"
    shutil.copy2(src, dst)
    shutil.copy2(src, out_dir / "best_model.pth")
    print(f"✓ Saved: {dst}")


if __name__ == "__main__":
    main()
