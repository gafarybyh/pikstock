"""context.py — path bersama dan App FastAPI dipegang modul ini (hindari import melingkar)."""

import threading
from pathlib import Path

from fastapi import FastAPI

BASE = Path(__file__).resolve().parent.parent
WEB = BASE / "web"
GENERATE = BASE / "generate"
UPLOADS = BASE / "uploads"
for d in (GENERATE, UPLOADS):
    d.mkdir(exist_ok=True)

ALLOWED_ROOTS = (UPLOADS, GENERATE)
ALLOWED_FOLDERS: set[str] = set()
ALLOWED_LOCK = threading.Lock()


def _resolve(path) -> Path | None:
    """Path absolut yang sudah dinormalkan, atau None bila tidak valid."""
    try:
        return Path(path).resolve(strict=False)
    except (OSError, ValueError):
        return None


def allow_folder(folder) -> str | None:
    """Daftarkan folder hasil dialog/scan sebagai sumber file yang sah."""
    p = _resolve(folder)
    if p is None or not p.is_dir():
        return None
    with ALLOWED_LOCK:
        ALLOWED_FOLDERS.add(str(p).lower())
    return str(p)


def is_allowed(path) -> bool:
    """True bila path berada di UPLOADS/GENERATE atau di folder yang sudah dipilih user."""
    p = _resolve(path)
    if p is None:
        return False
    if any(p == root or root in p.parents for root in ALLOWED_ROOTS):
        return True
    with ALLOWED_LOCK:
        folders = tuple(ALLOWED_FOLDERS)
    for folder in folders:
        root = Path(folder)
        if p == root or root in p.parents:
            return True
    return False


def require_allowed(path) -> Path:
    """Seperti is_allowed, tetapi melempar 403 untuk path di luar lingkup tool."""
    from fastapi import HTTPException

    p = _resolve(path)
    if p is None or not is_allowed(p):
        raise HTTPException(403, "path di luar lingkup tool")
    return p


app = FastAPI(title="Image Keyword Generator", docs_url=None, redoc_url=None)


@app.middleware("http")
async def revalidate_static(request, call_next):
    """Aset /static selalu divalidasi ulang -> edit CSS/JS langsung terpakai."""
    resp = await call_next(request)
    if request.url.path.startswith("/static/"):
        resp.headers["Cache-Control"] = "no-cache"
    return resp
