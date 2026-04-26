import logging

from fastapi import APIRouter, File, UploadFile
from fastapi import HTTPException

from ..models.schemas import PredictResponse, PredictionResult
from ..services.image_service import save_upload
from ..services.model_service import ModelNotReady, predict_image

router = APIRouter(prefix="/api", tags=["predict"])
log = logging.getLogger("predict")


@router.post("/predict", response_model=PredictResponse)
async def predict(image: UploadFile = File(...)):
    request_id, saved_path = await save_upload(image)
    try:
        label, confidence = predict_image(saved_path)
    except ModelNotReady as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    log.info("predict request_id=%s label=%s confidence=%s path=%s", request_id, label, confidence, saved_path)
    return PredictResponse(
        request_id=request_id,
        result=PredictionResult(label=label, confidence=confidence),
    )
