# Vision Service - Member 4 (SIH 26117)

**Multimodal image analysis using Qwen3-VL 4B**

This is a self-contained Python module for image understanding. It wraps Ollama's Qwen3-VL model and exposes a simple interface for the rest of the team.

---

## 🎯 Public Interface

Other team members only need to know about **ONE function**:

```python
from src.vision_service import VisionService

service = VisionService()

result = service.analyze_image(
    image_path="drawing.jpg",
    prompt="What components are in this P&ID?"
)

print(result)
# {
#     "status": "success",
#     "analysis": "I see pumps, valves, flow meters...",
#     "confidence": 0.85,
#     "image_path": "drawing.jpg",
#     "model": "qwen3-vl:4b"
# }
```

That's it. **Member 1 (Backend)** and **Member 3 (Agent)** don't need to know how vision works internally.

---

## 📋 Setup

### Prerequisites
- Ollama installed and running (`ollama serve`)
- Qwen3-VL 4B model downloaded (`ollama pull qwen3-vl:4b`)
- Python 3.9+

### Install

```bash
pip install -r requirements.txt
```

### Run Tests

```bash
python tests/test_vision.py
```

---

## 🖼️ Capabilities

### 1. Basic Image Analysis
```python
result = service.analyze_image(
    "scanned_inspection_report.jpg",
    "What are the key findings?"
)
```

### 2. OCR (Extract Text from Scanned Documents)
```python
text = service.extract_text_from_image("document.pdf")
# Returns: All text from document as string
```

### 3. Engineering Drawing Analysis
```python
result = service.analyze_drawing("P&ID.png")
# Returns: Components, connections, labels, specifications
```

### 4. Handwritten Document Recognition
```python
result = service.analyze_handwritten_document("handwritten_note.jpg")
# Returns: Transcription, document type, signatures
```

---

## 📊 Model Information

```
Model: qwen3-vl:4b
- Capabilities: ["vision", "completion", "tools", "thinking"]
- Size: 3.3 GB
- Quantization: Q4_K_M
- Context Length: 262,144 tokens
- Parameter Size: 4.4B
```

---

## 🔌 Integration Points

### For Member 1 (Backend / FastAPI)
Expose via REST API:
```python
@app.post("/api/vision/analyze")
async def analyze_image_api(image: UploadFile, prompt: str):
    result = service.analyze_image(image.filename, prompt)
    return result
```

### For Member 3 (Agent / LangGraph)
Use as a tool in the agent:
```python
def vision_tool(image_path: str, prompt: str) -> dict:
    service = VisionService()
    return service.analyze_image(image_path, prompt)

# Register with LangGraph
agent_state["tools"]["vision"] = vision_tool
```

---

## 🚨 Troubleshooting

### Error: "Ollama service not running"
```bash
ollama serve
```

### Error: "Image not found"
- Check file path is absolute or relative to current working directory
- Ensure file exists and is readable

### Inference timeout
- Model might be loading for first time
- GPU memory might be full
- Try with smaller image or shorter prompt

### Out of memory
- Qwen3-VL 4B requires ~6GB GPU memory
- Check available VRAM
- Reduce batch size or image resolution

---

## 📝 Development Notes

### Internal Structure
```
src/
├── vision_service.py    ← Main VisionService class (public interface)
├── ollama_client.py     ← Low-level Ollama API wrapper (internal)
└── __init__.py          ← Package exports
```

### Adding New Analysis Types
Add new methods to `VisionService` class:
```python
def analyze_inspection_report(self, image_path: str) -> dict:
    """Custom analysis for inspection reports"""
    prompt = "Extract defects, severity, and recommendations..."
    return self.analyze_image(image_path, prompt)
```

---

## ✅ Testing Checklist

- [ ] Ollama running and accessible
- [ ] Qwen3-VL 4B model loaded
- [ ] Test script runs without errors
- [ ] Analyze a JPEG image
- [ ] Analyze a PNG image
- [ ] Analyze a scanned PDF
- [ ] Extract text with OCR
- [ ] Analyze engineering drawing
- [ ] Verify no external API calls (network monitor)

---

## 🔒 Security & Sovereignty

✅ **Zero External Calls**
- All inference happens on-premises via Ollama
- No cloud APIs used
- No data leaves the organization
- Network traffic: Localhost only (127.0.0.1:11434)

---

## 📞 Team Contacts

- **Member 1 (Backend)**: Integration with FastAPI
- **Member 2 (RAG)**: Document indexing
- **Member 3 (Agent)**: Vision tool invocation
- **Member 5 (Frontend)**: Upload UI

---

**Status**: ✅ Ready for integration  
**Last Updated**: 2026-09-01
