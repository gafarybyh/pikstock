"""routes_image.py — generate gambar dari prompt via endpoint image OpenAI-compatible."""

import asyncio

from fastapi import Body, HTTPException

from kwgen.image_gen import N_MAX, PROMPT_MAX, SIZES

from .context import app
from .jobs import image_one


@app.post("/api/image/generate")
async def image_generate(body: dict = Body(...)):
    prompt = str(body.get("prompt", "")).strip()
    if not prompt:
        raise HTTPException(400, "Prompt wajib diisi")
    if len(prompt) > PROMPT_MAX:
        raise HTTPException(400, f"Prompt maksimal {PROMPT_MAX} karakter")
    try:
        n = int(body.get("n", 1))
    except (TypeError, ValueError):
        raise HTTPException(400, "Jumlah gambar harus berupa angka") from None
    if not 1 <= n <= N_MAX:
        raise HTTPException(400, f"Jumlah gambar harus 1–{N_MAX}")
    size = str(body.get("size") or "").strip() or None
    if size and size not in SIZES:
        raise HTTPException(400, "Ukuran gambar tidak didukung")
    res = await asyncio.to_thread(image_one, prompt, n=n, size=size)
    if res["status"] != "ok":
        raise HTTPException(500, res.get("error", "gagal"))
    return res
