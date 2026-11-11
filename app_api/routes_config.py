"""routes_config.py — baca/simpan pengaturan (config.json). Kunci API tak pernah dikirim utuh."""

from pathlib import Path

from fastapi import HTTPException

import core
from kwgen.image_gen import SIZES as IMAGE_SIZES

from .context import app


def key_hint(key: str) -> str:
    """Hanya 4 karakter terakhir — key penuh tidak pernah dikirim ke browser."""
    return ("•" * 8 + key[-4:]) if len(key) > 8 else ("•" * len(key) if key else "")


@app.get("/api/config")
def api_config():
    raw = core.read_config()
    key = core.api_key()
    return {
        "model": core.MODELS[0] if core.MODELS else "",
        "fallbacks": core.MODELS[1:],
        "router": core.CFG.get("router_url", ""),
        "pil": core.HAVE_PIL,
        "router_url": raw.get("router_url", ""),
        "fallback_models": raw.get("fallback_models") or [],
        "has_key": bool(key),
        "key_hint": key_hint(key),
        "max_image_side": int(raw.get("max_image_side", 1024)),
        "timeout_seconds": int(raw.get("timeout_seconds", 120)),
        "temp_dir": raw.get("temp_dir", "tmp"),
        "max_keywords": core.max_keywords(),
        "max_signal_terms": core.max_signal_terms(),
        "keyword_caps": core.KEYWORD_CAPS,
        "image_base_url": raw.get("image_base_url", ""),
        "image_model": raw.get("image_model", "flux-2-flex"),
        "image_size": raw.get("image_size", "1024x1024"),
        "image_has_key": bool(str(raw.get("image_api_key", "")).strip()),
        "image_key_hint": key_hint(str(raw.get("image_api_key", "")).strip()),
    }


@app.put("/api/config")
def api_config_save(body: dict):
    router_url = str(body.get("router_url", "")).strip()
    model = str(body.get("model", "")).strip()
    if not router_url.startswith(("http://", "https://")):
        raise HTTPException(400, "Base URL harus diawali http:// atau https://")
    if not model:
        raise HTTPException(400, "Model utama wajib diisi")

    fallbacks = body.get("fallback_models") or []
    if isinstance(fallbacks, str):
        fallbacks = fallbacks.splitlines()
    if not isinstance(fallbacks, list):
        raise HTTPException(400, "Fallback model harus berupa daftar")
    clean = []
    for item in fallbacks:
        m = str(item).strip()
        if m and m != model and m not in clean:
            clean.append(m)

    try:
        max_side = int(body.get("max_image_side", 1024))
        timeout = int(body.get("timeout_seconds", 120))
        max_kw = int(body.get("max_keywords", 30))
        max_sig = int(body.get("max_signal_terms", 150))
    except (TypeError, ValueError):
        raise HTTPException(400, "Sisi gambar, timeout, dan jumlah keyword harus berupa angka") from None
    if not 256 <= max_side <= 4096:
        raise HTTPException(400, "Sisi maksimal gambar harus 256–4096 px")
    if not 10 <= timeout <= 600:
        raise HTTPException(400, "Timeout harus 10–600 detik")
    if not 5 <= max_kw <= 30:
        raise HTTPException(400, "Jumlah keyword harus 5–30")
    if not 20 <= max_sig <= 500:
        raise HTTPException(400, "Jumlah keyword cek sinyal harus 20–500")

    temp_dir = str(body.get("temp_dir", "tmp")).strip() or "tmp"
    if Path(temp_dir).is_absolute() or ".." in Path(temp_dir).parts:
        raise HTTPException(400, "Folder sementara harus path relatif di dalam proyek")

    updates = {
        "router_url": router_url,
        "model": model,
        "fallback_models": clean,
        "max_image_side": max_side,
        "timeout_seconds": timeout,
        "temp_dir": temp_dir,
        "max_keywords": max_kw,
        "max_signal_terms": max_sig,
    }
    api_key = str(body.get("api_key", "")).strip()
    if api_key:  # kosong = pertahankan key lama
        updates["api_key"] = api_key

    image_url = str(body.get("image_base_url", "")).strip()
    image_model = str(body.get("image_model", "")).strip()
    image_size = str(body.get("image_size", "")).strip()
    if image_url and not image_url.startswith(("http://", "https://")):
        raise HTTPException(400, "Base URL image harus diawali http:// atau https://")
    if image_size and image_size not in IMAGE_SIZES:
        raise HTTPException(400, "Ukuran gambar tidak didukung")
    updates["image_base_url"] = image_url
    updates["image_model"] = image_model or "flux-2-flex"
    updates["image_size"] = image_size or "1024x1024"
    image_key = str(body.get("image_api_key", "")).strip()
    if image_key:
        updates["image_api_key"] = image_key

    try:
        core.save_config(updates)
    except OSError as e:
        raise HTTPException(500, f"Gagal menyimpan config: {e}") from e
    return {"ok": True, **api_config()}
