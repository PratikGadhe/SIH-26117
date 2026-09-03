from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from vision.src.vision_service import VisionService

app = FastAPI(title="Vision API")
service: Optional[VisionService] = None

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".pdf"}


def get_service() -> VisionService:
    global service
    if service is None:
        try:
            service = VisionService()
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    return service


async def save_upload(file: UploadFile) -> str:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Unsupported image or PDF file type")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    with NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
        temp_file.write(contents)
        return temp_file.name


@app.post("/api/vision/analyze")
async def analyze_image_api(file: UploadFile = File(...), prompt: str = Form(...)):
    temp_path = await save_upload(file)
    try:
        return get_service().analyze_image(temp_path, prompt)
    finally:
        Path(temp_path).unlink(missing_ok=True)


@app.post("/api/vision/ocr")
async def extract_text_api(file: UploadFile = File(...)):
    temp_path = await save_upload(file)
    try:
        return {"text": get_service().extract_text_from_image(temp_path)}
    finally:
        Path(temp_path).unlink(missing_ok=True)


@app.post("/api/vision/pdf")
async def analyze_pdf_api(file: UploadFile = File(...), prompt: str = Form("Extract all text and data from this document.")):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix != ".pdf":
        raise HTTPException(status_code=415, detail="PDF endpoint requires a .pdf file")

    temp_path = await save_upload(file)
    try:
        return get_service().analyze_pdf_document(temp_path, prompt)
    finally:
        Path(temp_path).unlink(missing_ok=True)
