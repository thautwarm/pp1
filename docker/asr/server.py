"""Qwen3-ASR-1.7B served over an OpenAI-compatible transcription API.

Endpoints
---------
POST /v1/audio/transcriptions   multipart/form-data (OpenAI Whisper shape)
GET  /health                    readiness (the model is loaded before uvicorn starts)

The model directory is taken from ASR_MODEL (default /models/Qwen3-ASR-1.7B).
"""

from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from qwen_asr import Qwen3ASRModel
import base64, os, tempfile, time, torch

MODEL = os.getenv("ASR_MODEL", "/models/Qwen3-ASR-1.7B")

LANGUAGE_CODES = {
    "zh": "Chinese", "en": "English", "yue": "Cantonese", "ar": "Arabic",
    "de": "German", "fr": "French", "es": "Spanish", "pt": "Portuguese",
    "id": "Indonesian", "it": "Italian", "ko": "Korean", "ru": "Russian",
    "th": "Thai", "vi": "Vietnamese", "ja": "Japanese", "tr": "Turkish",
    "hi": "Hindi", "ms": "Malay", "nl": "Dutch", "sv": "Swedish",
    "da": "Danish", "fi": "Finnish", "pl": "Polish", "cs": "Czech",
    "fil": "Filipino", "fa": "Persian", "el": "Greek", "ro": "Romanian",
    "hu": "Hungarian", "mk": "Macedonian",
}
LANGUAGE_NAMES = {name.lower(): name for name in LANGUAGE_CODES.values()}


def _resolve_language(value: str | None) -> str | None:
    """Accept ISO-639-1 codes, English names, or anything the model understands."""
    if not value or not value.strip():
        return None
    raw = value.strip()
    key = raw.lower().replace("_", "-")
    base = key.split("-")[0]
    if key in LANGUAGE_NAMES:
        return LANGUAGE_NAMES[key]
    if base in LANGUAGE_NAMES:
        return LANGUAGE_NAMES[base]
    if base in LANGUAGE_CODES:
        return LANGUAGE_CODES[base]
    return raw


print(f"Loading {MODEL} ...", flush=True)
asr_model = Qwen3ASRModel.from_pretrained(
    pretrained_model_name_or_path=MODEL,
    torch_dtype=torch.float16,
    device_map="auto",
)
print("Ready.", flush=True)

app = FastAPI()


@app.middleware("http")
async def log_timing(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start
    print(f"{request.method} {request.url.path} {response.status_code} {elapsed:.3f}s", flush=True)
    return response


class InputAudio(BaseModel):
    data: str
    format: str = "wav"


class TranscriptionRequest(BaseModel):
    model: str | None = None
    input_audio: InputAudio


def _transcribe_file(filepath: str, language: str | None = None, context: str = "") -> str:
    results = asr_model.transcribe(
        audio=filepath,
        context=context or "",
        language=language or None,
    )
    return results[0].text


async def _handle_transcription(
    file: UploadFile,
    language: str | None,
    prompt: str | None,
    response_format: str,
):
    fmt = (response_format or "json").strip().lower()
    if fmt not in ("json", "text"):
        raise HTTPException(
            status_code=400,
            detail=f"unsupported response_format '{response_format}', supported: json, text",
        )
    suffix = os.path.splitext(file.filename or ".wav")[1]
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
    try:
        try:
            text = _transcribe_file(
                tmp.name,
                language=_resolve_language(language),
                context=prompt or "",
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    finally:
        os.unlink(tmp.name)
    if fmt == "text":
        return PlainTextResponse(text)
    return {"text": text}


@app.post("/v1/audio/transcriptions")
@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    model: str | None = Form(None),
    language: str | None = Form(None),
    prompt: str | None = Form(None),
    response_format: str = Form("json"),
    temperature: float | None = Form(None),
):
    return await _handle_transcription(file, language, prompt, response_format)


@app.post("/audio/transcriptions")
async def audio_transcriptions(req: TranscriptionRequest):
    """Legacy base64 endpoint kept for older clients."""
    suffix = f".{req.input_audio.format.lstrip('.')}"
    raw = base64.b64decode(req.input_audio.data)
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(raw)
    try:
        text = _transcribe_file(tmp.name)
        return {"text": text}
    finally:
        os.unlink(tmp.name)


@app.get("/health")
async def health():
    return {"status": "ok", "model": MODEL}
