from __future__ import annotations

import os
import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .captions import parse_srt
from .render import render_video


PROJECT_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = PROJECT_DIR / "web"
JOBS_DIR = Path(os.getenv("STREAMER_GENERATOR_JOBS_DIR", Path.home() / ".streamer-video-generator" / "jobs"))
MAX_UPLOAD_BYTES = int(os.getenv("STREAMER_GENERATOR_MAX_UPLOAD_BYTES", 1_500_000_000))
MAX_TOTAL_UPLOAD_BYTES = MAX_UPLOAD_BYTES * 2 + 2_000_000
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}
executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="video-render")
jobs: dict[str, dict] = {}
jobs_lock = threading.Lock()

app = FastAPI(title="Streamer Shorts Studio", docs_url=None, redoc_url=None)
app.mount("/assets", StaticFiles(directory=WEB_DIR), name="assets")


def _cleanup_old_jobs() -> None:
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    cutoff = time.time() - 24 * 60 * 60
    for item in JOBS_DIR.iterdir():
        try:
            if item.is_dir() and item.stat().st_mtime < cutoff:
                shutil.rmtree(item)
        except OSError:
            continue


def _update_job(job_id: str, progress: float, message: str) -> None:
    with jobs_lock:
        if job_id in jobs:
            jobs[job_id].update(progress=round(max(0, min(1, progress)), 3), message=message)


def _render_job(job_id: str, directory: Path, options: dict) -> None:
    with jobs_lock:
        jobs[job_id].update(status="processing", message="Preparing source videos", progress=0.05)
    try:
        output = render_video(
            directory / options["facecam_name"],
            directory / options["gameplay_name"],
            directory / "streamer-short.mp4",
            subtitle_text=options["subtitle_text"],
            style=options["caption_style"],
            facecam_height=options["facecam_height"],
            fps=options["fps"],
            streamer_volume=options["streamer_volume"],
            gameplay_volume=options["gameplay_volume"],
            facecam_focus=options["facecam_focus"],
            gameplay_focus=options["gameplay_focus"],
            on_progress=lambda progress, message: _update_job(job_id, progress, message),
        )
        with jobs_lock:
            jobs[job_id].update(status="done", progress=1, message="MP4 is ready", output=output.name)
    except Exception as error:  # surfaced to the local UI as a readable render error
        with jobs_lock:
            jobs[job_id].update(status="error", message=str(error)[:4000], progress=0)


async def _save_upload(upload: UploadFile, target: Path) -> int:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(400, f"Unsupported video file type: {suffix or 'unknown'}")
    total = 0
    try:
        with target.open("wb") as destination:
            while chunk := await upload.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "Each video must be smaller than the configured upload limit.")
                destination.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    if total == 0:
        target.unlink(missing_ok=True)
        raise HTTPException(400, "The uploaded video is empty.")
    return total


@app.on_event("startup")
async def startup() -> None:
    _cleanup_old_jobs()


@app.middleware("http")
async def same_origin_api(request: Request, call_next):
    if request.url.path.startswith("/api/") and request.method in {"POST", "PUT", "DELETE"}:
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            raise HTTPException(403, "Requests must come from this local studio.")
    return await call_next(request)


@app.get("/")
async def home():
    return FileResponse(WEB_DIR / "index.html")


@app.post("/api/jobs", status_code=202)
async def create_job(
    facecam: UploadFile = File(...),
    gameplay: UploadFile = File(...),
    subtitle_text: str = Form(""),
    caption_style: str = Form("bold"),
    facecam_height: int = Form(768),
    fps: int = Form(30),
    streamer_volume: float = Form(1),
    gameplay_volume: float = Form(1),
    facecam_focus_x: float = Form(50),
    facecam_focus_y: float = Form(50),
    gameplay_focus_x: float = Form(50),
    gameplay_focus_y: float = Form(50),
):
    if caption_style not in {"bold", "clean", "neon"}:
        raise HTTPException(400, "Choose a supported caption style.")
    if facecam_height not in (576, 672, 768, 864, 960) or fps not in (30, 60):
        raise HTTPException(400, "Choose a supported layout size and frame rate.")
    for label, value in (("Streamer volume", streamer_volume), ("Gameplay volume", gameplay_volume)):
        if not 0 <= value <= 2:
            raise HTTPException(400, f"{label} must be between 0 and 200%.")
    focus_values = (facecam_focus_x, facecam_focus_y, gameplay_focus_x, gameplay_focus_y)
    if any(not 0 <= value <= 100 for value in focus_values):
        raise HTTPException(400, "Crop focus controls must be between 0 and 100%.")
    if len(subtitle_text.encode("utf-8")) > 1_000_000:
        raise HTTPException(413, "Subtitle text is too large.")
    try:
        parse_srt(subtitle_text)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error

    job_id = uuid.uuid4().hex
    directory = JOBS_DIR / job_id
    directory.mkdir(parents=True, exist_ok=False)
    facecam_name = "facecam" + Path(facecam.filename or "").suffix.lower()
    gameplay_name = "gameplay" + Path(gameplay.filename or "").suffix.lower()
    try:
        facecam_size = await _save_upload(facecam, directory / facecam_name)
        gameplay_size = await _save_upload(gameplay, directory / gameplay_name)
        sizes = (facecam_size, gameplay_size)
        if sum(sizes) > MAX_TOTAL_UPLOAD_BYTES:
            raise HTTPException(413, "The combined uploads exceed the configured limit.")
    except Exception:
        shutil.rmtree(directory, ignore_errors=True)
        raise
    finally:
        await facecam.close()
        await gameplay.close()

    options = {
        "facecam_name": facecam_name,
        "gameplay_name": gameplay_name,
        "subtitle_text": subtitle_text,
        "caption_style": caption_style,
        "facecam_height": facecam_height,
        "fps": fps,
        "streamer_volume": streamer_volume,
        "gameplay_volume": gameplay_volume,
        "facecam_focus": (facecam_focus_x / 100, facecam_focus_y / 100),
        "gameplay_focus": (gameplay_focus_x / 100, gameplay_focus_y / 100),
    }
    with jobs_lock:
        jobs[job_id] = {"status": "queued", "progress": 0, "message": "Waiting for the render slot"}
    executor.submit(_render_job, job_id, directory, options)
    return {"id": job_id, "status": "queued"}


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "This render job was not found. Restarting the studio clears its job list.")
    result = {key: value for key, value in job.items() if key != "output"}
    if job.get("status") == "done":
        result["download_url"] = f"/api/jobs/{job_id}/download"
    return {"id": job_id, **result}


@app.get("/api/jobs/{job_id}/download")
async def download_job(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)
    if not job or job.get("status") != "done":
        raise HTTPException(404, "This video is not ready for download.")
    path = JOBS_DIR / job_id / job["output"]
    if not path.is_file():
        raise HTTPException(404, "The rendered video has been cleaned up.")
    return FileResponse(path, media_type="video/mp4", filename="streamer-short.mp4")
