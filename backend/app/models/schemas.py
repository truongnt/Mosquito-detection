from datetime import datetime

from pydantic import BaseModel, Field


class PredictionResult(BaseModel):
    label: str
    confidence: float = Field(ge=0.0, le=1.0)


class PredictResponse(BaseModel):
    request_id: str
    result: PredictionResult


class TrainingRunCreate(BaseModel):
    total_epochs: int = Field(default=10, ge=1, le=500)
    learning_rate: float = Field(default=0.001, gt=0.0, le=1.0)
    batch_size: int = Field(default=32, ge=1, le=4096)
    note: str | None = Field(default=None, max_length=2000)


class TrainingRunOut(BaseModel):
    id: str
    created_at: datetime
    created_by: str
    status: str
    progress: float
    current_epoch: int
    total_epochs: int
    params_json: dict | None = None
    metrics_json: dict | None = None
    artifact_path: str | None = None
    error_message: str | None = None


class TrainingEventOut(BaseModel):
    id: int
    run_id: str
    ts: datetime
    level: str
    message: str
    payload_json: dict | None = None
