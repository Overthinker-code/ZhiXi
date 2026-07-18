from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from app.core.config import settings

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")
_MIME_BY_EXTENSION = {
    ".c": {"text/plain", "text/x-c"},
    ".cpp": {"text/plain", "text/x-c++"},
    ".doc": {"application/msword", "application/octet-stream"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/zip"},
    ".java": {"text/plain", "text/x-java-source"},
    ".gif": {"image/gif"},
    ".jpeg": {"image/jpeg"},
    ".jpg": {"image/jpeg"},
    ".js": {"text/javascript", "application/javascript", "text/plain"},
    ".md": {"text/markdown", "text/plain"},
    ".markdown": {"text/markdown", "text/plain"},
    ".mmd": {"text/markdown", "text/plain"},
    ".mp3": {"audio/mpeg", "audio/mp3"},
    ".mp4": {"video/mp4"},
    ".pdf": {"application/pdf"},
    ".png": {"image/png"},
    ".ppt": {"application/vnd.ms-powerpoint", "application/octet-stream"},
    ".pptx": {"application/vnd.openxmlformats-officedocument.presentationml.presentation", "application/zip"},
    ".py": {"text/x-python", "text/plain"},
    ".sql": {"application/sql", "text/plain"},
    ".ts": {"text/typescript", "application/typescript", "text/plain"},
    ".txt": {"text/plain"},
    ".wav": {"audio/wav", "audio/x-wav"},
    ".webm": {"video/webm"},
    ".webp": {"image/webp"},
}


def sanitize_filename(filename: str | None, fallback: str = "upload") -> str:
    leaf = Path(filename or fallback).name.replace("\x00", "")
    sanitized = _SAFE_NAME.sub("_", leaf).strip("._")
    return (sanitized or fallback)[:160]


def validate_upload_metadata(
    file: UploadFile,
    *,
    allowed_extensions: set[str],
) -> tuple[str, str]:
    safe_name = sanitize_filename(file.filename)
    extension = Path(safe_name).suffix.lower()
    if extension not in allowed_extensions:
        raise HTTPException(status_code=415, detail="Unsupported file extension")
    content_type = (file.content_type or "application/octet-stream").split(";", 1)[0].lower()
    allowed_mimes = _MIME_BY_EXTENSION.get(extension)
    if allowed_mimes and content_type not in allowed_mimes:
        raise HTTPException(status_code=415, detail="File MIME type does not match its extension")
    file.filename = safe_name
    return safe_name, extension


async def validate_upload(
    file: UploadFile,
    *,
    allowed_extensions: set[str],
) -> tuple[str, str]:
    safe_name, extension = validate_upload_metadata(
        file, allowed_extensions=allowed_extensions
    )
    header = await file.read(16)
    await file.seek(0)
    signatures = {
        ".pdf": lambda value: value.startswith(b"%PDF"),
        ".png": lambda value: value.startswith(b"\x89PNG\r\n\x1a\n"),
        ".jpg": lambda value: value.startswith(b"\xff\xd8\xff"),
        ".jpeg": lambda value: value.startswith(b"\xff\xd8\xff"),
        ".gif": lambda value: value.startswith((b"GIF87a", b"GIF89a")),
        ".docx": lambda value: value.startswith(b"PK"),
        ".pptx": lambda value: value.startswith(b"PK"),
        ".mp4": lambda value: len(value) >= 12 and value[4:8] == b"ftyp",
        ".mp3": lambda value: value.startswith(b"ID3") or (len(value) >= 2 and value[0] == 0xff and value[1] & 0xe0 == 0xe0),
        ".mmd": lambda value: b"\x00" not in value,
        ".wav": lambda value: len(value) >= 12 and value.startswith(b"RIFF") and value[8:12] == b"WAVE",
        ".webm": lambda value: value.startswith(b"\x1a\x45\xdf\xa3"),
        ".webp": lambda value: len(value) >= 12 and value.startswith(b"RIFF") and value[8:12] == b"WEBP",
    }
    check = signatures.get(extension)
    if check and not check(header):
        raise HTTPException(status_code=415, detail="File content does not match its extension")
    return safe_name, extension


async def read_upload_limited(file: UploadFile, max_bytes: int | None = None) -> bytes:
    limit = max_bytes or settings.MAX_UPLOAD_SIZE
    chunks: list[bytes] = []
    size = 0
    while True:
        chunk = await file.read(min(1024 * 1024, limit + 1 - size))
        if not chunk:
            break
        size += len(chunk)
        if size > limit:
            raise HTTPException(status_code=413, detail="Uploaded file is too large")
        chunks.append(chunk)
    return b"".join(chunks)


def random_storage_name(extension: str) -> str:
    return f"{uuid4().hex}{extension}"
