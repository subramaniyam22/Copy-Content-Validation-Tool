"""Content Validation Tool — FastAPI application entry point."""
import sys
import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.repositories.db import init_db, close_db
from app.utils.logging import logger

# Force ProactorEventLoop on Windows for Playwright compatibility
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: init DB on startup, close on shutdown."""
    logger.info("Starting Content Validation Tool...")
    await init_db()
    yield
    await close_db()
    logger.info("Shutting down Content Validation Tool.")


app = FastAPI(
    title="Content Validation Tool",
    description="Next-gen website copy validation platform with layered analysis",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──── Register API routes ────
from app.api.routes.discovery import router as discovery_router
from app.api.routes.guidelines import router as guidelines_router
from app.api.routes.validate import router as validate_router
from app.api.routes.exports import router as exports_router
from app.api.routes.scans import router as scans_router
from app.api.routes.exclusions import router as exclusions_router

app.include_router(discovery_router)
app.include_router(guidelines_router)
app.include_router(validate_router)
app.include_router(exports_router)
app.include_router(scans_router)
app.include_router(exclusions_router)


# ──── Legacy endpoints (deprecated, kept for backward compat) ────
from fastapi import HTTPException, UploadFile, File, Form
from typing import List
import json


@app.post("/check-grammar", deprecated=True)
async def check_grammar_legacy(
    base_url: str = Form(...),
    menu_options: str = Form(...),
    guidelines: List[UploadFile] = File(default=None),
):
    """Legacy endpoint — use POST /api/validate instead."""
    return {"message": "This endpoint is deprecated. Use POST /api/validate with the new workflow."}


@app.post("/check-lv", deprecated=True)
async def check_lv_legacy(
    base_url: str = Form(...),
    menu_options: str = Form(...),
    copy_file: UploadFile = File(...),
):
    """Legacy endpoint — use POST /api/validate instead."""
    return {"message": "This endpoint is deprecated. Use POST /api/validate with the new workflow."}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "2.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
