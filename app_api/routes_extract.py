"""routes_extract.py — unggah satu gambar, hasilkan deskripsi saja."""

import asyncio
import uuid
from pathlib import Path

from fastapi import File, HTTPException, UploadFile

from .context import UPLOADS, app
from .jobs import extract_one

MAX_UPLOAD_BYTES = 40 * 1024 * 1024


def save_upload(file: UploadFile) -> Path:
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
    return dest


@app.post("/api/extract")
async def extract_upload(file: UploadFile = File(...)):
    dest = save_upload(file)
    try:
        res = await asyncio.to_thread(extract_one, str(dest),
                                      filename=file.filename or dest.name)
    except Exception:
        dest.unlink(missing_ok=True)
        raise
    if res["status"] != "ok":
        dest.unlink(missing_ok=True)
        raise HTTPException(500, res.get("error", "gagal"))
    return res
