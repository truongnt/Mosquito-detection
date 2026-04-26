from datetime import datetime

from pydantic import BaseModel, Field


class PredictionResult(BaseModel):
    label: str
    confidence: float = Field(ge=0.0, le=1.0)


class PredictResponse(BaseModel):
    request_id: str
    result: PredictionResult


class TrainingRunCreate(BaseModel):
    dataset: str = Field(default="mosquitodl", max_length=64)
    total_epochs: int = Field(default=10, ge=1, le=500)
    img_size: int = Field(default=224, ge=64, le=2048)
    learning_rate: float = Field(default=0.001, gt=0.0, le=1.0)
    batch_size: int = Field(default=32, ge=1, le=4096)
    base_model: str = Field(
        default="yolo26n-cls.pt",
        max_length=128,
        description="Ultralytics weights name or local path (e.g. yolo26n-cls.pt)",
    )
    augment_enabled: bool = Field(default=True, description="Enable training-time data augmentation")
    aug_hsv_h: float = Field(default=0.015, ge=0.0, le=0.1)
    aug_hsv_s: float = Field(default=0.7, ge=0.0, le=1.0)
    aug_hsv_v: float = Field(default=0.4, ge=0.0, le=1.0)
    aug_degrees: float = Field(default=10.0, ge=0.0, le=90.0)
    aug_translate: float = Field(default=0.1, ge=0.0, le=1.0)
    aug_scale: float = Field(default=0.5, ge=0.0, le=1.0)
    aug_shear: float = Field(default=2.0, ge=0.0, le=10.0)
    aug_perspective: float = Field(default=0.0, ge=0.0, le=0.01)
    aug_flip_lr: float = Field(default=0.5, ge=0.0, le=1.0, description="Probability of horizontal flip")
    aug_flip_ud: float = Field(default=0.0, ge=0.0, le=1.0, description="Probability of vertical flip")
    aug_mosaic: float = Field(default=0.8, ge=0.0, le=1.0)
    aug_mixup: float = Field(default=0.0, ge=0.0, le=1.0)
    aug_copy_paste: float = Field(default=0.0, ge=0.0, le=1.0)
    aug_erasing: float = Field(default=0.0, ge=0.0, le=1.0)
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


class AdminJobCreate(BaseModel):
    dataset: str = Field(default="mosquitodl", max_length=64)
    max_per_label: int = Field(default=500, ge=1, le=20000)
    val_ratio: float = Field(default=0.1, ge=0.0, le=0.5)
    test_ratio: float = Field(default=0.1, ge=0.0, le=0.5)
    seed: int = Field(default=42, ge=0, le=2_147_483_647)


class AdminJobOut(BaseModel):
    id: str
    kind: str
    created_at: datetime
    created_by: str
    status: str
    progress: float
    params_json: dict | None = None
    result_json: dict | None = None
    error_message: str | None = None


class AdminJobEventOut(BaseModel):
    id: int
    job_id: str
    ts: datetime
    level: str
    message: str
    payload_json: dict | None = None
