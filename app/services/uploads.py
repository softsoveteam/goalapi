from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from app.core.config import settings

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".zip",
    ".txt",
}


def uploads_root() -> Path:
    path = Path(settings.upload_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_upload(task_id: int, file: UploadFile) -> tuple[str, str, int, str]:
    original = Path(file.filename or "file").name
    suffix = Path(original).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="File type not allowed")
    data = file.file.read()
    size = len(data)
    if size <= 0:
        raise HTTPException(status_code=400, detail="Empty file")
    if size > settings.max_upload_bytes:
        raise HTTPException(status_code=400, detail="File is larger than 15 MB")
    stored = "{0}{1}".format(uuid4().hex, suffix)
    folder = uploads_root() / str(task_id)
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / stored
    dest.write_bytes(data)
    content_type = file.content_type or "application/octet-stream"
    return original[:255], stored, size, content_type


def file_path(task_id: int, stored_name: str) -> Path:
    return uploads_root() / str(task_id) / stored_name
