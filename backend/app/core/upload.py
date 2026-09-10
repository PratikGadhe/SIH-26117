"""Secure temporary file boundary and validation for uploaded assets."""

from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path
import tempfile
import uuid

from fastapi import HTTPException, status
from starlette.datastructures import UploadFile

MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_IMAGE_SIZE_BYTES = MAX_UPLOAD_SIZE_BYTES  # Backward compatibility
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_DOCUMENT_EXTENSIONS = {".pdf"}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_DOCUMENT_EXTENSIONS


def validate_image_magic_bytes(data: bytes, extension: str) -> bool:
    """Verify that file content matches expected image format headers."""
    if extension == ".png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if extension in {".jpg", ".jpeg"}:
        return data.startswith(b"\xff\xd8\xff")
    if extension == ".webp":
        return len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    return False


def validate_pdf_magic_bytes(data: bytes) -> bool:
    """Verify that file content matches expected PDF document header."""
    return data.startswith(b"%PDF-")


def validate_file_magic_bytes(data: bytes, extension: str) -> bool:
    """Validate magic bytes for any supported image or document extension."""
    if extension in ALLOWED_IMAGE_EXTENSIONS:
        return validate_image_magic_bytes(data, extension)
    if extension in ALLOWED_DOCUMENT_EXTENSIONS:
        return validate_pdf_magic_bytes(data)
    return False


@contextmanager
def secure_temporary_upload(upload_file: UploadFile) -> Iterator[tuple[str, str]]:
    """
    Validate and safely persist an uploaded file (image or PDF) to an isolated temporary location.

    Yields a tuple of (temp_path, file_kind) where file_kind is either "image" or "pdf".
    Guarantees file removal upon context exit, even if exceptions occur.
    """
    raw_filename = upload_file.filename or ""
    suffix = Path(raw_filename).suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file format. Allowed formats: PNG, JPG, JPEG, WEBP, PDF.",
        )

    # Read content up to max limit + 1 byte to detect oversizing safely
    content = upload_file.file.read(MAX_UPLOAD_SIZE_BYTES + 1)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=getattr(status, "HTTP_413_CONTENT_TOO_LARGE", 413),
            detail="Uploaded file exceeds the maximum permitted size of 10 MB.",
        )

    if not validate_file_magic_bytes(content, suffix):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File content does not match the stated file format.",
        )

    # Generate an isolated temporary path outside the workspace
    safe_filename = f"cognivault_upload_{uuid.uuid4().hex}{suffix}"
    temp_dir = Path(tempfile.gettempdir())
    temp_path = temp_dir / safe_filename

    temp_path.write_bytes(content)
    file_kind = "pdf" if suffix in ALLOWED_DOCUMENT_EXTENSIONS else "image"
    try:
        yield str(temp_path), file_kind
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass


@contextmanager
def secure_temporary_image(upload_file: UploadFile) -> Iterator[str]:
    """
    Validate and safely persist an uploaded image to an isolated temporary location.

    Guarantees file removal upon context exit, even if exceptions occur.
    """
    raw_filename = upload_file.filename or ""
    suffix = Path(raw_filename).suffix.lower()

    if suffix not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file format. Allowed formats: PNG, JPG, JPEG, WEBP.",
        )

    with secure_temporary_upload(upload_file) as (temp_path, _):
        yield temp_path
