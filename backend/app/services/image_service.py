import os
import uuid
from pathlib import Path

from fastapi import UploadFile

from ..config import settings


def ensure_upload_dir() -> None:
    os.makedirs(settings.upload_dir, exist_ok=True)


async def save_upload(file: UploadFile) -> tuple[str, str]:
    ensure_upload_dir()
    request_id = uuid.uuid4().hex
    filename = file.filename or "image"
    safe_name = filename.replace("\\", "_").replace("/", "_")
    dest = Path(settings.upload_dir) / f"{request_id}_{safe_name}"

    content = await file.read()
    dest.write_bytes(content)
    return request_id, str(dest)
