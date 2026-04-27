from __future__ import annotations

import logging

from ..services.model_registry import ModelSpec, get_model_spec
from .model_service import get_model

log = logging.getLogger("predict.multi")


def _yolo_predict_aggregate(paths: list[str]) -> tuple[str, float]:
    import torch

    model = get_model()
    res = model.predict(source=paths, device="cpu", verbose=False)
    if not res:
        raise RuntimeError("No prediction results")

    probs_list = []
    names = None
    for r in res:
        if names is None:
            names = getattr(r, "names", None)
        p = getattr(r, "probs", None)
        if p is None:
            raise RuntimeError("Model is not a classification model (missing probs)")
        data = getattr(p, "data", None)
        if data is None:
            raise RuntimeError("Missing probs.data")
        probs_list.append(data.detach().float().cpu())

    if not probs_list:
        raise RuntimeError("No probs found")

    avg = torch.stack(probs_list, dim=0).mean(dim=0)
    top1 = int(torch.argmax(avg).item())
    conf = float(avg[top1].item())
    label = None
    if isinstance(names, dict):
        label = names.get(top1)
    if not isinstance(label, str):
        label = str(top1)
    return label, conf


def _vectech_xception_predict(paths: list[str], spec: ModelSpec) -> tuple[str, float]:
    """
    Minimal inference adapter for VecTech novel-species-detection Xception .pth weights.

    WARNING: The upstream repository uses a CC BY-NC 4.0 license (non-commercial).
    This adapter expects you to have a compatible `.pth` state_dict file and the
    corresponding label list in the model spec config.
    """
    try:
        import pretrainedmodels  # noqa: F401
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("Missing dependency 'pretrainedmodels' for vectech_xception model") from exc

    import torch
    from PIL import Image
    from torchvision import transforms

    cfg = spec.config or {}
    weights_path = cfg.get("weights_path")
    if not isinstance(weights_path, str) or not weights_path.strip():
        raise RuntimeError("vectech_xception requires config.weights_path")
    labels = cfg.get("labels")
    if not isinstance(labels, list) or not labels:
        raise RuntimeError("vectech_xception requires config.labels (list[str])")
    labels = [str(x) for x in labels]

    imsize = int(cfg.get("imsize") or 299)

    from pretrainedmodels.models import xception
    import torch.nn as nn

    device = "cpu"
    model = xception(pretrained=None)
    model.last_linear = nn.Linear(in_features=2048, out_features=len(labels), bias=True)

    sd = torch.load(weights_path, map_location=device)
    if isinstance(sd, dict) and "state_dict" in sd and isinstance(sd["state_dict"], dict):
        sd = sd["state_dict"]
    if not isinstance(sd, dict):
        raise RuntimeError("Unsupported weights format; expected state_dict dict")

    cleaned = {}
    for k, v in sd.items():
        kk = str(k)
        if kk.startswith("module."):
            kk = kk[len("module.") :]
        cleaned[kk] = v
    model.load_state_dict(cleaned, strict=False)
    model.eval()

    tfm = transforms.Compose(
        [
            transforms.Resize(int(imsize * 1.11)),
            transforms.CenterCrop(imsize),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
        ]
    )

    probs_list = []
    with torch.no_grad():
        for p in paths:
            img = Image.open(p).convert("RGB")
            x = tfm(img).unsqueeze(0)
            logits = model(x)
            probs = torch.softmax(logits, dim=1)[0].detach().float().cpu()
            probs_list.append(probs)

    avg = torch.stack(probs_list, dim=0).mean(dim=0)
    top1 = int(torch.argmax(avg).item())
    conf = float(avg[top1].item())
    return labels[top1], conf


def predict_for_model(model_id: str, image_paths: list[str]) -> tuple[str, float]:
    if model_id == "yolo":
        return _yolo_predict_aggregate(image_paths)

    spec = get_model_spec(model_id)
    if spec.type == "vectech_xception":
        return _vectech_xception_predict(image_paths, spec)

    raise RuntimeError(f"Unsupported model type: {spec.type}")
