import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export YOLO classification model")
    parser.add_argument("--model", default="ml/models/saved/best_model.pt")
    parser.add_argument("--format", default="onnx", choices=["onnx", "torchscript"])
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    from ultralytics import YOLO

    model_path = Path(args.model).resolve()
    if not model_path.exists():
        raise SystemExit(f"Model not found: {model_path}")

    model = YOLO(str(model_path))
    out = model.export(format=args.format, device=args.device)
    print(f"✓ Exported: {out}")


if __name__ == "__main__":
    main()
