"""routes_pick.py — pilih folder/file native, thumbnail, scan."""

import hashlib
import subprocess
import sys
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse

import core

from .context import BASE, GENERATE, allow_folder, app, require_allowed
from .jobs import make_thumb, scan_folder


def native_dialog(mode):
    exe = [sys.executable, str(BASE / "paths.py"), mode]
    try:
        r = subprocess.run(exe, capture_output=True, text=True, timeout=300,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception as e:
        raise HTTPException(500, f"Dialog gagal dibuka: {e}") from e
    out = (r.stdout or "").strip()
    if r.returncode != 0 or not out:
        return None
    return out


@app.post("/api/select-folder")
def select_folder():
    folder = native_dialog("--folder")
    if not folder:
        return {"cancelled": True}
    allow_folder(folder)
    return {"cancelled": False, "folder": folder, "images": scan_folder(folder)}


@app.post("/api/select-file")
def select_file():
    path = native_dialog("--file")
    if not path:
        return {"cancelled": True}
    allow_folder(Path(path).parent)
    return {"cancelled": False, "path": path, "name": Path(path).name}


@app.get("/api/thumb")
def api_thumb(path: str):
    """Thumbnail on-demand untuk grid batch (belum pernah diproses)."""
    src = require_allowed(path)
    if not src.is_file() or src.suffix.lower() not in core.IMAGE_EXTS:
        raise HTTPException(400, "bukan gambar")
    key = hashlib.sha1(f"{src}:{src.stat().st_mtime_ns}".encode()).hexdigest()[:16]
    dest = GENERATE / f"_{key}.webp"
    if not dest.exists():
        if not make_thumb(src, f"_{key}"):
            raise HTTPException(415, "Pillow tidak tersedia untuk thumbnail")
    return FileResponse(dest, media_type="image/webp")


@app.get("/api/scan")
def api_scan(folder: str):
    allow_folder(folder)
    return {"folder": folder, "images": scan_folder(folder)}
