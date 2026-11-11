"""routes_history.py — riwayat run, statistik, ekspor CSV."""

import csv
import io
import json
from pathlib import Path

from fastapi import Body, HTTPException
from fastapi.responses import FileResponse, Response

import core
import db
from kwgen.formats import fmt_all

from .context import app, require_allowed


@app.get("/api/history")
def history(q: str = "", limit: int = 50, offset: int = 0, status: str = "", source: str = "",
            scope: str = "", favorite: bool = False, market: str = ""):
    if scope and scope not in ("keyword", "extract", "image"):
        raise HTTPException(400, "scope harus keyword, extract, atau image")

        raise HTTPException(400, "market tidak dikenal")
    runs, total = db.list_runs(q=q, limit=limit, offset=offset, status=status or None,
                               source=source or None, scope=scope or None, favorite=favorite,
                               market=market or None)
    return {"runs": runs, "total": total}


@app.post("/api/history/{run_id}/favorite")
def history_favorite(run_id: int, body: dict):
    fav = body.get("favorite")
    if not isinstance(fav, bool):
        raise HTTPException(400, "favorite harus true atau false")
    if not db.set_favorite(run_id, fav):
        raise HTTPException(404, "Tidak ditemukan")
    return {"id": run_id, "favorite": fav}


@app.post("/api/history/seen")
def history_seen(body: dict):
    """Nama file (lowercase) yang sudah pernah diproses sukses di riwayat."""
    names = body.get("filenames") or []
    if not isinstance(names, list):
        raise HTTPException(400, "filenames harus berupa daftar")
    return {"seen": db.seen_filenames(names)}


@app.get("/api/history/{run_id}")
def history_one(run_id: int):
    r = db.get_run(run_id)
    if not r:
        raise HTTPException(404, "Tidak ditemukan")
    return r


@app.get("/api/history/{run_id}/image")
def history_image(run_id: int):
    r = db.get_run(run_id)
    if not r:
        raise HTTPException(404, "Tidak ditemukan")
    src = r.get("path") or ""
    if not src or not Path(src).is_file():
        raise HTTPException(404, "Berkas sumber sudah tidak ada")
    return FileResponse(src)


@app.post("/api/history/{run_id}/regenerate")
def history_regenerate(run_id: int, body: dict | None = Body(None)):
    from .jobs import extract_one, picked_markets, run_one

    r = db.get_run(run_id)
    if not r:
        raise HTTPException(404, "Run ini sudah tidak ada di riwayat (mungkin baru dihapus). Muat ulang daftar riwayat.")
    is_extract = r.get("source", "").startswith("extract")
    src = r.get("path") or ""
    if not src:
        raise HTTPException(400, "Run ini tidak menyimpan lokasi gambar")
    if not Path(src).is_file():
        raise HTTPException(410, "Berkas sumber sudah tidak ada di disk, jadi tidak bisa di-generate ulang.")
    try:
        require_allowed(src)
    except HTTPException as exc:
        raise HTTPException(403,
            "Folder sumber run ini belum diizinkan pada sesi sekarang. "
            "Buka lagi folder tersebut lewat Batch folder, lalu coba generate ulang.") from exc
    if is_extract:
        res = extract_one(src, filename=r.get("filename") or None, thumb_src=src, overwrite_id=run_id)
    else:
        payload = body if isinstance(body, dict) else {}
        marketplaces = payload.get("marketplaces")
        only = picked_markets(marketplaces) if isinstance(marketplaces, list) and marketplaces else None
        res = run_one(src, source=r.get("source") or "upload", filename=r.get("filename") or None,
                      thumb_src=src, only=only, overwrite_id=run_id)
    if res["status"] != "ok":
        raise HTTPException(500, res.get("error", "gagal"))
    return res


@app.delete("/api/history/keyword")
def history_clear_keyword():
    return {"deleted": db.clear_runs("keyword")}


@app.delete("/api/history/extract")
def history_clear_extract():
    return {"deleted": db.clear_runs("extract")}


@app.delete("/api/history/image")
def history_clear_image():
    return {"deleted": db.clear_runs("image")}


@app.delete("/api/history/{run_id}")
def history_delete(run_id: int):
    ok = db.delete_run(run_id)
    if not ok:
        raise HTTPException(404, "Tidak ditemukan")
    return {"ok": True}


@app.delete("/api/history")
def history_clear(ids: str = "", scope: str = ""):
    if ids.strip():
        return {"deleted": db.delete_runs(ids.split(","))}
    if scope and scope not in ("keyword", "extract", "image"):
        raise HTTPException(400, "scope harus keyword, extract, atau image")



@app.get("/api/stats")
def api_stats():
    return db.stats()


def csv_response(rows, filename):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(core.CSV_HEADER)
    w.writerows(rows)
    data = ("\ufeff" + buf.getvalue()).encode("utf-8")  # BOM: Excel aman
    return Response(data, media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.get("/api/history/{run_id}/export.csv")
def export_run(run_id: int):
    r = db.get_run(run_id)
    if not r or r.get("status") != "ok" or not r.get("data"):
        raise HTTPException(404, "Run tidak ditemukan atau tanpa data")
    if r["data"].get("kind") == "extract":
        raise HTTPException(404, "Run extract tidak punya data keyword")
    rows = core.csv_rows(r["data"], r["id"], r["filename"], r["created_at"])
    return csv_response(rows, f"keywords-{run_id}.csv")

def _keyword_run_or_404(run_id: int) -> dict:
    r = db.get_run(run_id)
    if not r or r.get("status") != "ok" or not r.get("data"):
        raise HTTPException(404, "Run tidak ditemukan atau tanpa data")
    if r["data"].get("kind") == "extract":
        raise HTTPException(404, "Run extract tidak punya data keyword")
    return r

@app.get("/api/history/{run_id}/export.txt")
def export_run_txt(run_id: int):
    r = _keyword_run_or_404(run_id)
    stem = Path(r["filename"]).stem or f"keywords-{run_id}"
    return Response(fmt_all(r["data"]).encode("utf-8"), media_type="text/plain; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{stem}.txt"'})

@app.get("/api/history/{run_id}/export.json")
def export_run_json(run_id: int):
    r = _keyword_run_or_404(run_id)
    stem = Path(r["filename"]).stem or f"keywords-{run_id}"
    body = json.dumps(r["data"], indent=2, ensure_ascii=False).encode("utf-8")
    return Response(body, media_type="application/json; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{stem}.json"'})


@app.get("/api/export.csv")
def export_all(q: str = "", status: str = "", source: str = ""):
    rows = []
    for r in db.export_runs(q=q, status=status or None, source=source or None):
        rows += core.csv_rows(r["data"], r["id"], r["filename"], r["created_at"])
    return csv_response(rows, "keywords-semua.csv")
