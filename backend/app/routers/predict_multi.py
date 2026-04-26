import json
import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..models.schemas import ModelPredictionOut, MultiPredictResponse
from ..services.image_service import save_upload
from ..services.predict_multi import predict_for_model

router = APIRouter(prefix="/api", tags=["predict"])
log = logging.getLogger("predict.multi")


def _parse_models(raw: str | None) -> list[str]:
    if not raw:
        return ["yolo"]
    s = raw.strip()
    if not s:
        return ["yolo"]
    if s.startswith("["):
        try:
            v = json.loads(s)
            if isinstance(v, list) and v:
                return [str(x) for x in v if str(x)]
        except Exception:
            pass
    return [p.strip() for p in s.split(",") if p.strip()] or ["yolo"]


@router.post("/predict_multi", response_model=MultiPredictResponse)
async def predict_multi(
    images: list[UploadFile] = File(...),
    models: str | None = Form(default=None, description="comma-separated model ids or JSON list"),
):
    if not images:
        raise HTTPException(status_code=400, detail="No images uploaded")
    model_ids = _parse_models(models)

    request_id = None
    saved_paths: list[str] = []
    for img in images:
        rid, saved = await save_upload(img)
        request_id = request_id or rid
        saved_paths.append(saved)

    results: list[ModelPredictionOut] = []
    for mid in model_ids:
        try:
            label, conf = predict_for_model(mid, saved_paths)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Model {mid} failed: {exc}") from exc
        results.append(ModelPredictionOut(model_id=mid, label=label, confidence=conf))

    log.info("predict_multi request_id=%s models=%s images=%s", request_id, model_ids, len(saved_paths))
    return MultiPredictResponse(request_id=request_id or "unknown", results=results)

