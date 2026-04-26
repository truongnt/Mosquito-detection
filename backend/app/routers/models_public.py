from fastapi import APIRouter

from ..services.model_registry import list_enabled_models

router = APIRouter(prefix="/api", tags=["models"])


@router.get("/models")
def list_models():
    specs = list_enabled_models()
    return [
        {
            "id": s.id,
            "name": s.name,
            "type": s.type,
            "description": s.description,
            "license": s.license,
            "noncommercial_only": s.noncommercial_only,
        }
        for s in specs
    ]

