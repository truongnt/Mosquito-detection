import logging

from fastapi import APIRouter, File, UploadFile

from ..models.schemas import PredictResponse, PredictionResult
from ..services.image_service import save_upload
from ..services.model_service import predict_stub

router = APIRouter(prefix="/api", tags=["predict"])
log = logging.getLogger("predict")


@router.post("/predict", response_model=PredictResponse)
async def predict(image: UploadFile = File(...)):
    request_id, saved_path = await save_upload(image)
    label, confidence = predict_stub(saved_path)
    log.info("predict request_id=%s label=%s confidence=%s path=%s", request_id, label, confidence, saved_path)
    return PredictResponse(
        request_id=request_id,
        result=PredictionResult(label=label, confidence=confidence),
    )
