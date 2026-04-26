import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate YOLO classification model on val/test")
    parser.add_argument("--model", default="ml/models/saved/best_model.pt")
    parser.add_argument("--data", default="data/processed/mosquitodl")
    parser.add_argument("--split", default="test", choices=["train", "val", "test"])
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    from ultralytics import YOLO

    model_path = Path(args.model).resolve()
    data_root = Path(args.data).resolve()
    if not model_path.exists():
        raise SystemExit(f"Model not found: {model_path}")
    if not (data_root / args.split).exists():
        raise SystemExit(f"Split folder not found: {data_root/args.split}")

    model = YOLO(str(model_path))
    metrics = model.val(data=str(data_root), split=args.split, device=args.device, verbose=True)
    try:
        print(metrics)
    except Exception:
        pass


if __name__ == "__main__":
    main()
