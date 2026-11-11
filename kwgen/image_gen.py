"""kwgen.image_gen - POST ke endpoint image generation OpenAI-compatible."""

import json
import uuid
import urllib.error
import urllib.request
from pathlib import Path

from .config import CFG

SIZES = ("auto", "1024x1024", "1536x1024", "1024x1536", "1792x1024", "1024x1792")
PROMPT_MAX = 4000
N_MAX = 4
DOWNLOAD_MAX = 30 * 1024 * 1024


def images_url():
    base = str(CFG.get("image_base_url", "")).strip().rstrip("/")
    return base if base.endswith("/images/generations") else base + "/images/generations"


def api_key():
    return str(CFG.get("image_api_key", "")).strip()


def generate(prompt, n=1, size=None):
    """Kembalikan list URL gambar. Respons gagal/kosong -> RuntimeError."""
    prompt = str(prompt or "").strip()
    if not prompt:
        raise ValueError("Prompt wajib diisi")
    if len(prompt) > PROMPT_MAX:
        raise ValueError(f"Prompt maksimal {PROMPT_MAX} karakter")
    if not 1 <= n <= N_MAX:
        raise ValueError(f"Jumlah gambar 1–{N_MAX}")
    size = size or str(CFG.get("image_size", "1024x1024"))
    if size not in SIZES:
        raise ValueError("Ukuran tidak didukung")
    if not str(CFG.get("image_base_url", "")).strip():
        raise RuntimeError("Base URL image belum diisi di Pengaturan")
    if not api_key():
        raise RuntimeError("Kunci API image belum diisi di Pengaturan")

    body = {
        "model": str(CFG.get("image_model", "flux-2-flex")),
        "prompt": prompt,
        "n": n,
        "size": size,
        "response_format": "url",
    }
    req = urllib.request.Request(
        images_url(), data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {api_key()}"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=int(CFG.get("timeout_seconds", 120))) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        msg = e.read().decode(errors="replace")[:400]
        raise RuntimeError(f"Generate gagal, HTTP {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Tidak bisa konek ke endpoint image: {e.reason}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Respons image rusak: {e}") from e

    urls = [item.get("url") for item in (data.get("data") or []) if item.get("url")]
    if not urls:
        raise RuntimeError("Respons tidak berisi gambar")
    return urls


def download(url, dest_dir):
    """Unduh satu gambar hasil ke dest_dir. Return nama file lokal."""
    if not str(url).startswith(("http://", "https://")):
        raise RuntimeError("URL gambar tidak valid")
    with urllib.request.urlopen(url, timeout=int(CFG.get("timeout_seconds", 120))) as r:
        blob = r.read(DOWNLOAD_MAX + 1)
    if len(blob) > DOWNLOAD_MAX:
        raise RuntimeError("Gambar hasil terlalu besar")
    ext = Path(url.split("?")[0]).suffix.lower()
    ext = ext if ext in (".png", ".jpg", ".jpeg", ".webp") else ".png"
    name = f"img_{uuid.uuid4().hex[:12]}{ext}"
    (Path(dest_dir) / name).write_bytes(blob)
    return name


def image_size(path):
    """Ukuran nyata 'WIDTHxHEIGHT' dari file gambar, atau '' bila tidak terbaca."""
    try:
        from PIL import Image
        with Image.open(path) as im:
            return f"{im.width}x{im.height}"
    except Exception:
        return ""
