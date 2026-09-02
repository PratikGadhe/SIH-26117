from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse
from pathlib import Path

from vision.src.vision_service import VisionService

app = FastAPI(title="Vision API")
service = VisionService()


@app.post("/api/vision/analyze")
async def analyze_image_api(file: UploadFile = File(...), prompt: str = Form(...)):
    temp_dir = Path("/tmp")
    temp_dir.mkdir(exist_ok=True)
    temp_path = temp_dir / file.filename
    contents = await file.read()
    temp_path.write_bytes(contents)
    return service.analyze_image(str(temp_path), prompt)


@app.post("/api/vision/ocr")
async def extract_text_api(file: UploadFile = File(...)):
    temp_dir = Path("/tmp")
    temp_dir.mkdir(exist_ok=True)
    temp_path = temp_dir / file.filename
    temp_path.write_bytes(await file.read())
    return {"text": service.extract_text_from_image(str(temp_path))}


@app.post("/api/vision/pdf")
async def analyze_pdf_api(file: UploadFile = File(...), prompt: str = Form("Extract all text and data from this document.")):
    temp_dir = Path("/tmp")
    temp_dir.mkdir(exist_ok=True)
    temp_path = temp_dir / file.filename
    temp_path.write_bytes(await file.read())
    return service.analyze_pdf_document(str(temp_path), prompt)
