from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models.config_kv import AppConfigKV


@dataclass(frozen=True)
class ModelSpec:
    id: str
    name: str
    type: str
    description: str | None = None
    license: str | None = None
    noncommercial_only: bool = False
    config: dict[str, Any] | None = None


def _get_models_kv(db: Session) -> AppConfigKV:
    row = db.get(AppConfigKV, "models")
    if row and isinstance(row.value_json, dict):
        return row
    now = datetime.now(timezone.utc)
    row = AppConfigKV(key="models", value_json={"enabled": ["yolo"], "registry": {}}, updated_at=now)
    db.add(row)
    db.commit()
    return row


def list_enabled_models() -> list[ModelSpec]:
    """
    Public listing of enabled models.

    Notes:
    - Always includes the built-in Ultralytics YOLO classification model ("yolo").
    - Additional models can be registered under app_config key "models".
    """
    db = SessionLocal()
    try:
        kv = _get_models_kv(db)
        value = kv.value_json if isinstance(kv.value_json, dict) else {}
        enabled = value.get("enabled") if isinstance(value.get("enabled"), list) else ["yolo"]
        registry = value.get("registry") if isinstance(value.get("registry"), dict) else {}

        specs: list[ModelSpec] = [
            ModelSpec(
                id="yolo",
                name="YOLO (active)",
                type="ultralytics_yolo_cls",
                description="Ultralytics YOLO classification model using the active weights on server.",
                config={},
            )
        ]

        for mid in enabled:
            if not isinstance(mid, str) or not mid or mid == "yolo":
                continue
            raw = registry.get(mid)
            if not isinstance(raw, dict):
                continue
            specs.append(
                ModelSpec(
                    id=mid,
                    name=str(raw.get("name") or mid),
                    type=str(raw.get("type") or "unknown"),
                    description=raw.get("description") if isinstance(raw.get("description"), str) else None,
                    license=raw.get("license") if isinstance(raw.get("license"), str) else None,
                    noncommercial_only=bool(raw.get("noncommercial_only", False)),
                    config={k: v for k, v in raw.items() if k not in {"name", "type", "description", "license", "noncommercial_only"}},
                )
            )

        return specs
    finally:
        db.close()


def get_model_spec(model_id: str) -> ModelSpec:
    if model_id == "yolo":
        return ModelSpec(
            id="yolo",
            name="YOLO (active)",
            type="ultralytics_yolo_cls",
            description="Ultralytics YOLO classification model using the active weights on server.",
            config={},
        )

    db = SessionLocal()
    try:
        kv = _get_models_kv(db)
        value = kv.value_json if isinstance(kv.value_json, dict) else {}
        enabled = value.get("enabled") if isinstance(value.get("enabled"), list) else []
        if model_id not in enabled:
            raise KeyError(f"model not enabled: {model_id}")
        registry = value.get("registry") if isinstance(value.get("registry"), dict) else {}
        raw = registry.get(model_id)
        if not isinstance(raw, dict):
            raise KeyError(f"model not found in registry: {model_id}")
        return ModelSpec(
            id=model_id,
            name=str(raw.get("name") or model_id),
            type=str(raw.get("type") or "unknown"),
            description=raw.get("description") if isinstance(raw.get("description"), str) else None,
            license=raw.get("license") if isinstance(raw.get("license"), str) else None,
            noncommercial_only=bool(raw.get("noncommercial_only", False)),
            config={k: v for k, v in raw.items() if k not in {"name", "type", "description", "license", "noncommercial_only"}},
        )
    finally:
        db.close()

