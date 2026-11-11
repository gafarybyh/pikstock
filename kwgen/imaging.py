"""kwgen.imaging - buka gambar, turunkan ukuran, jadikan base64."""

import base64
import io
from pathlib import Path

from .config import CFG
from .constants import MIME

try:  # PIL opsional - tanpa ini hanya PNG/GIF yang bisa diproses apa adanya
    from PIL import Image
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False


_FORMAT = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG",
           ".webp": "WEBP", ".gif": "GIF", ".bmp": "BMP"}


def _format_for(ext):
    return _FORMAT.get(ext) or ext.lstrip(".").upper() or None


def _orientation(w, h):
    if not w or not h:
        return None
    if abs(w - h) <= max(w, h) * 0.02:
        return "square"
    return "landscape" if w > h else "portrait"


def _has_alpha(im):
    if im.mode not in ("RGBA", "LA", "PA", "P") and "transparency" not in im.info:
        return False
    try:
        return im.convert("RGBA").getchannel("A").getextrema()[0] < 255
    except Exception:
        return None


def encode_image_meta(path):
    """-> (mime, base64_str, metadata). Metadata dari file asli, bukan hasil resize."""
    p = Path(path)
    ext = p.suffix.lower()
    mime = MIME.get(ext, "image/png")
    raw = p.read_bytes()
    meta = {"ext": ext.lstrip("."), "format": _format_for(ext),
            "width": None, "height": None, "orientation": None, "alpha": None}
    if HAVE_PIL:
        im = Image.open(io.BytesIO(raw))
        if not meta["format"]:
            meta["format"] = (im.format or "").upper() or None
        w, h = im.size
        meta["width"], meta["height"] = w, h
        meta["orientation"] = _orientation(w, h)
        meta["alpha"] = _has_alpha(im)
        side = int(CFG.get("max_image_side", 1024))
        if max(im.size) > side:
            im.thumbnail((side, side))
        buf = io.BytesIO()
        if im.mode in ("RGBA", "LA", "P"):
            im.save(buf, "PNG")
            mime = "image/png"
        else:
            im.convert("RGB").save(buf, "JPEG", quality=88)
            mime = "image/jpeg"
        raw = buf.getvalue()
    return mime, base64.b64encode(raw).decode(), meta


def encode_image(path):
    """-> (mime, base64_str). Downscale kalau PIL tersedia."""
    mime, b64, _ = encode_image_meta(path)
    return mime, b64
