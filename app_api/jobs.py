"""jobs.py — helper + state proses generate/batch dan antrean SSE."""

import asyncio
import json
import logging
import queue
import threading
import time
import uuid
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

import core
import db
import kwgen.image_gen as image_gen
import kwgen.router as _router

from .context import BASE, GENERATE, UPLOADS  # noqa: F401

JOBS: dict[int, dict] = {}
JOBS_LOCK = threading.Lock()
log = logging.getLogger(__name__)


def make_thumb(src: Path, stem: str) -> str:
    """Buat thumbnail webp 320px. Return nama file (relatif ke /generate)."""
    name = f"{stem}.webp"
    dest = GENERATE / name
    if dest.exists():
        return name
    if not core.HAVE_PIL:
        return ""
    try:
        from PIL import Image
        im = Image.open(src)
        im.thumbnail((320, 320))
        if im.mode not in ("RGB", "RGBA"):
            rgb = im.convert("RGB")
            rgb.save(dest, "WEBP", quality=80, method=4)
        else:
            im.save(dest, "WEBP", quality=80, method=4)
        return name
    except Exception as exc:
        log.warning("make_thumb gagal untuk %s: %s: %s", src, type(exc).__name__, exc)
        dest.unlink(missing_ok=True)
        return ""

def scan_folder(folder: str):
    p = Path(folder)
    if not p.is_dir():
        raise HTTPException(400, "Folder tidak ditemukan")
    files = sorted(
        (f for f in p.iterdir() if f.is_file() and f.suffix.lower() in core.IMAGE_EXTS),
        key=lambda f: f.name.lower())
    return [{"name": f.name, "path": str(f), "size": f.stat().st_size} for f in files]


def picked_markets(raw):
    """Validasi pilihan marketplace. None/absen -> None (semua, kompat lama)."""
    if raw is None:
        return None
    if isinstance(raw, str):
        raw = raw.split(",")
    if not isinstance(raw, list):
        raise HTTPException(400, "marketplaces harus berupa daftar")
    asked = {str(x).strip().lower() for x in raw}
    picked = [m for m in core.ALL_MARKETS if m in asked]
    if not picked:
        raise HTTPException(400, "Pilih minimal satu marketplace")
    return picked


def run_one(path: str, *, source="upload", batch_id=None, filename=None, thumb_src=None,
            only=None, overwrite_id=None):
    """Proses satu gambar + simpan ke riwayat. Return dict hasil."""
    t0 = time.time()
    name = filename or Path(path).name
    try:
        data = core.build_keywords(path, only=only)
        dur = int((time.time() - t0) * 1000)
        prev = db.get_run(overwrite_id) if overwrite_id else None
        if overwrite_id and prev is None:
            raise RuntimeError("Run tujuan generate ulang sudah tidak ada")
        prev_thumb = prev.get("thumb") if prev else None
        thumb = make_thumb(Path(thumb_src or path), f"{uuid.uuid4().hex[:12]}")
        if overwrite_id:
            saved = db.update_run(overwrite_id, thumb=thumb, data=data, model=data.get("model", ""),
                                  duration_ms=dur, status="ok", error=None)
            if not saved:
                (GENERATE / thumb).unlink(missing_ok=True)
                raise RuntimeError("Run tujuan generate ulang sudah tidak ada")
            run_id = overwrite_id
            if prev_thumb and prev_thumb != thumb:
                (GENERATE / prev_thumb).unlink(missing_ok=True)
        else:
            run_id = db.add_run(batch_id=batch_id, source=source, path=path, filename=name,
                                thumb=thumb, data=data, model=data.get("model", ""),
                                duration_ms=dur, status="ok")
        return {"id": run_id, "filename": name, "status": "ok", "data": data,
                "thumb": thumb, "duration_ms": dur}
    except Exception as e:
        dur = int((time.time() - t0) * 1000)
        if overwrite_id:
            db.update_run(overwrite_id, duration_ms=dur, status="error", error=str(e))
            run_id = overwrite_id
        else:
            run_id = db.add_run(batch_id=batch_id, source=source, path=path, filename=name,
                                status="error", error=str(e), duration_ms=dur)
        return {"id": run_id, "filename": name, "status": "error", "error": str(e),
                "duration_ms": dur}


def extract_one(path: str, *, filename=None, thumb_src=None, overwrite_id=None):
    """Ekstrak deskripsi gambar saja + simpan ke riwayat extract."""
    t0 = time.time()
    name = filename or Path(path).name
    try:
        description, attrs = core.extract_describe(path)
        dur = int((time.time() - t0) * 1000)
        model = _router.LAST_MODEL
        data = {
            "kind": "extract",
            "description": description,
            "model": model,
            "word_count": len(description.split()),
            **attrs,
        }
        prev = db.get_run(overwrite_id) if overwrite_id else None
        if overwrite_id and prev is None:
            raise RuntimeError("Run tujuan generate ulang sudah tidak ada")
        prev_thumb = prev.get("thumb") if prev else None
        thumb = make_thumb(Path(thumb_src or path), f"{uuid.uuid4().hex[:12]}")
        if overwrite_id:
            db.update_run(overwrite_id, thumb=thumb, data=data, model=model,
                          duration_ms=dur, status="ok", error=None)
            run_id = overwrite_id
            if prev_thumb and prev_thumb != thumb:
                (GENERATE / prev_thumb).unlink(missing_ok=True)
        else:
            run_id = db.add_run(source="extract", path=path, filename=name, thumb=thumb,
                                data=data, model=model, duration_ms=dur, status="ok")
        return {"id": run_id, "filename": name, "status": "ok", "data": data,
                "thumb": thumb, "duration_ms": dur}
    except Exception as e:
        dur = int((time.time() - t0) * 1000)
        if overwrite_id:
            db.update_run(overwrite_id, duration_ms=dur, status="error", error=str(e))
            run_id = overwrite_id
        else:
            run_id = db.add_run(source="extract", path=path, filename=name,
                                status="error", error=str(e), duration_ms=dur)
        return {"id": run_id, "filename": name, "status": "error", "error": str(e),
                "duration_ms": dur}


def image_one(prompt: str, *, n: int, size: str | None):
    """Generate gambar, unduh tiap URL ke GENERATE/, simpan ke riwayat image."""
    t0 = time.time()
    name = prompt[:60]
    try:
        urls = image_gen.generate(prompt, n=n, size=size)
        files = []
        for url in urls:
            files.append(image_gen.download(url, GENERATE))
        sizes = [image_gen.image_size(GENERATE / f) for f in files]
        dur = int((time.time() - t0) * 1000)
        data = {"kind": "image", "prompt": prompt, "sizes": sizes,
                "images": files, "model": image_gen.CFG.get("image_model", "")}
        run_id = db.add_run(source="image", filename=name, thumb=files[0], data=data,
                            model=data["model"], duration_ms=dur, status="ok")
        return {"id": run_id, "filename": name, "status": "ok", "data": data,
                "thumb": files[0], "duration_ms": dur}
    except Exception as e:
        dur = int((time.time() - t0) * 1000)
        run_id = db.add_run(source="image", filename=name, status="error",
                            error=str(e), duration_ms=dur)
        return {"id": run_id, "filename": name, "status": "error", "error": str(e),
                "duration_ms": dur}


def batch_worker(job, batch_id, folder, files, only=None):
    q = job["queue"]
    done = failed = 0
    for i, item in enumerate(files, 1):
        if job["cancel"].is_set():
            q.put({"type": "cancelled", "done": done, "failed": failed, "total": len(files)})
            db.update_batch(batch_id, status="cancelled", done=done, failed=failed,
                            finished_at=db.now())
            q.put(None)
            return
        path = item["path"]
        q.put({"type": "start", "index": i, "total": len(files), "filename": item["name"]})
        res = run_one(path, source="batch", batch_id=batch_id, only=only)
        if res["status"] == "ok":
            done += 1
            q.put({"type": "ok", "index": i, "total": len(files), "filename": item["name"],
                   "result": res})
        else:
            failed += 1
            q.put({"type": "error", "index": i, "total": len(files), "filename": item["name"],
                   "error": res.get("error", "")})
        db.update_batch(batch_id, done=done, failed=failed)
    if job["cancel"].is_set():  # dibatalkan saat gambar terakhir diproses
        db.update_batch(batch_id, status="cancelled", done=done, failed=failed,
                        finished_at=db.now())
        q.put({"type": "cancelled", "done": done, "failed": failed, "total": len(files)})
        q.put(None)
        return
    db.update_batch(batch_id, status="done", done=done, failed=failed, finished_at=db.now())
    q.put({"type": "done", "done": done, "failed": failed, "total": len(files)})
    q.put(None)


def sse_stream(batch_id: int, job) -> StreamingResponse:
    q = job["queue"]

    async def stream():
        loop = asyncio.get_running_loop()
        while True:
            try:
                item = await loop.run_in_executor(None, q.get, True, 30)
            except queue.Empty:
                yield ": keep-alive\n\n"
                continue
            if item is None:
                break
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
        with JOBS_LOCK:
            JOBS.pop(batch_id, None)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
