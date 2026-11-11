"""routes_signals.py — sinyal demand Google Suggest (batch + stream NDJSON)."""

import asyncio
import json

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

import core
import signals

from .context import app


def _signal_terms(body: dict) -> tuple:
    """-> (terms, requested). `requested` = jumlah unik SEBELUM kena cap."""
    raw = body.get("terms") or []
    if not isinstance(raw, list):
        raise HTTPException(400, "terms harus berupa daftar")
    terms, seen = [], set()
    for item in raw:
        t = str(item).strip()
        key = t.lower()
        if t and key not in seen:
            seen.add(key)
            terms.append(t)
    requested = len(terms)
    terms = terms[:core.max_signal_terms()]
    if not terms:
        raise HTTPException(400, "Tidak ada term untuk dicek")
    return terms, requested


@app.post("/api/signals")
async def api_signals(body: dict):
    terms, requested = _signal_terms(body)
    out = []
    for i, t in enumerate(terms):
        res = await asyncio.to_thread(signals.score_term, t)
        if not res.get("cached") and i < len(terms) - 1:
            await asyncio.sleep(0.3)  # sopan ke endpoint publik
        out.append(res)
    return {"signals": out, "total": len(terms), "requested": requested,
            "truncated": requested > len(terms)}


@app.post("/api/signals/stream")
async def api_signals_stream(body: dict):
    """NDJSON: satu baris JSON per term, dikirim begitu hasilnya siap."""
    terms, requested = _signal_terms(body)

    async def gen():
        for i, t in enumerate(terms):
            res = await asyncio.to_thread(signals.score_term, t)
            yield json.dumps(res, ensure_ascii=False) + "\n"
            if not res.get("cached") and i < len(terms) - 1:
                await asyncio.sleep(0.3)
        yield json.dumps({"done": True, "total": len(terms),
                          "requested": requested,
                          "truncated": requested > len(terms)}) + "\n"

    return StreamingResponse(
        gen(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
