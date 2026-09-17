import logging
import os

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

from backend.analyzer import review_code
from backend.cache import review_cache
from backend.config import settings
from backend.models import ReviewReport, ReviewRequest
from backend.report import to_markdown

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

app = FastAPI(
    title="AI Code Review & Vulnerability Detection Agent",
    description="Hybrid static-analysis + LLM code reviewer: bugs, security issues, "
    "code smells, severity, explanations, and fixes.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "llm_available": settings.llm_available,
        "model": settings.ANTHROPIC_MODEL if settings.llm_available else None,
        "cache": review_cache.stats(),
    }


@app.post("/api/review", response_model=ReviewReport)
def review(request: ReviewRequest):
    try:
        return review_code(request.code, request.filename, request.language)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error during review")
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@app.post("/api/review/file", response_model=ReviewReport)
async def review_file(file: UploadFile = File(...)):
    content = await file.read()
    try:
        code = content.decode("utf-8", errors="replace")
    except Exception:
        raise HTTPException(status_code=400, detail="Could not decode file as text.")
    try:
        return review_code(code, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/review/markdown", response_class=PlainTextResponse)
def review_markdown(request: ReviewRequest):
    try:
        report = review_code(request.code, request.filename, request.language)
        return to_markdown(report)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Serve the static frontend (index.html, app.js, style.css) at the root.
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
