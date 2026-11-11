"""routes_jobs.py — generate satu gambar, batch, cancel, SSE progres."""

import asyncio
import queue
import threading
import uuid
from pathlib import Path

from fastapi import File, Form, HTTPException, UploadFile

import db

from .context import UPLOADS, allow_folder, app, require_allowed
from .jobs import JOBS, JOBS_LOCK, batch_worker, picked_markets, run_one, scan_folder, sse_stream

MAX_UPLOAD_BYTES = 40 * 1024 * 1024


@app.post("/api/generate")
async def generate_upload(file: UploadFile = File(...), marketplaces: str = Form(None)):
    ext = Path(file.filename or "img.png").suffix.lower() or ".png"
    dest = UPLOADS / f"{uuid.uuid4().hex[:12]}{ext}"
    written = 0
    with dest.open("wb") as f:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            written += len(chunk)
            if written > MAX_UPLOAD_BYTES:
                f.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(413, "Berkas terlalu besar")
            f.write(chunk)
    try:
        res = await asyncio.to_thread(run_one, str(dest), source="upload",
                                      filename=file.filename or dest.name, thumb_src=str(dest),
                                      only=picked_markets(marketplaces))
    except Exception:
        dest.unlink(missing_ok=True)
        raise
    if res["status"] != "ok":
        dest.unlink(missing_ok=True)
        raise HTTPException(500, res.get("error", "gagal"))
    return res


@app.post("/api/batch")
def start_batch(body: dict):
    folder = body.get("folder", "")
    if folder:
        allow_folder(folder)
    files = body.get("files") or scan_folder(folder)
    if not files:
        raise HTTPException(400, "Tidak ada gambar untuk diproses")
    for item in files:
        require_allowed(item.get("path", ""))
    only = picked_markets(body.get("marketplaces"))
    project_id = db.upsert_project(folder)
    batch_id = db.create_batch(project_id, folder, len(files))
    job = {"queue": queue.Queue(), "cancel": threading.Event()}
    with JOBS_LOCK:
        JOBS[batch_id] = job
    threading.Thread(target=batch_worker, args=(job, batch_id, folder, files, only), daemon=True).start()
    return {"batch_id": batch_id, "total": len(files)}


@app.post("/api/batch/{batch_id}/cancel")
def cancel_batch(batch_id: int):
    job = JOBS.get(batch_id)
    if not job:
        raise HTTPException(404, "Batch tidak aktif")
    job["cancel"].set()
    return {"ok": True}


@app.get("/api/events/{batch_id}")
async def events(batch_id: int):
    job = JOBS.get(batch_id)
    if not job:
        raise HTTPException(404, "Batch tidak aktif")
    return sse_stream(batch_id, job)
