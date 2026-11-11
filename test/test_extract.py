"""Self-check fitur Image Extract: scope riwayat + simpan deskripsi."""

import asyncio
import tempfile
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import HTTPException, UploadFile

import db


def _temp_db():
    return Path(tempfile.mkdtemp()) / "history.db"


def test_scope_history():
    saved = db.DB_PATH
    db.DB_PATH = _temp_db()
    try:
        db.init()
        kw_id = db.add_run(source="upload", filename="keyword.png", data={"subject": "x"})
        ex_id = db.add_run(source="extract", filename="extract.png",
                           data={"kind": "extract", "description": "deskripsi"})
        rows, total = db.list_runs(scope="keyword")
        assert total == 1 and rows[0]["id"] == kw_id
        rows, total = db.list_runs(scope="extract")
        assert total == 1 and rows[0]["id"] == ex_id
        assert db.seen_filenames(["keyword.png", "extract.png"]) == ["keyword.png"]
        assert [r["id"] for r in db.export_runs()] == [kw_id]
        assert db.clear_runs("keyword") == 1
        assert db.list_runs()[1] == 1
        assert db.list_runs(scope="extract")[0][0]["id"] == ex_id
        assert db.clear_runs("extract") == 1
        assert db.list_runs()[1] == 0
    finally:
        db.DB_PATH = saved


def _upload(name):
    return UploadFile(file=BytesIO(b"abc"), filename=name)


def test_clear_routes():
    from app_api.routes_history import history_clear_extract, history_clear_keyword

    saved = db.DB_PATH
    db.DB_PATH = _temp_db()
    db.init()
    try:
        db.add_run(source="upload", filename="keyword.png", data={"subject": "x"})
        db.add_run(source="extract", filename="extract.png",
                   data={"kind": "extract", "description": "deskripsi"})
        assert history_clear_extract()["deleted"] == 1
        assert db.list_runs(scope="keyword")[1] == 1
        assert history_clear_keyword()["deleted"] == 1
        assert db.list_runs()[1] == 0
    finally:
        db.DB_PATH = saved


def test_extract_route(monkeypatch):
    import app_api.routes_extract as rx

    monkeypatch.setattr(rx, "UPLOADS", Path(tempfile.mkdtemp()))
    monkeypatch.setattr(rx, "extract_one", lambda path, filename=None: {
        "id": 7, "filename": filename, "status": "ok",
        "data": {"kind": "extract", "description": "Deskripsi uji.", "word_count": 2},
        "thumb": "", "duration_ms": 10,
    })
    res = asyncio.run(rx.extract_upload(_upload("uji.png")))
    assert res["data"]["kind"] == "extract"

    failed = Path(tempfile.mkdtemp())
    monkeypatch.setattr(rx, "UPLOADS", failed)
    monkeypatch.setattr(rx, "extract_one", lambda path, filename=None: {
        "id": 8, "filename": filename, "status": "error", "error": "gagal",
    })
    with pytest.raises(HTTPException) as exc:
        asyncio.run(rx.extract_upload(_upload("gagal.png")))
    assert exc.value.status_code == 500
    assert not list(failed.iterdir())


def test_extract_one(monkeypatch):
    import app_api.jobs as jobs

    saved = db.DB_PATH
    db.DB_PATH = _temp_db()
    db.init()
    monkeypatch.setattr(jobs.core, "extract_describe", lambda path: (
        "Gambar bunga di atas meja.",
        {"asset_type": "illustration", "style": "watercolor", "mood": ["calm"],
         "tone": "pastel", "colors": ["pink", "green"], "lighting": "",
         "composition": "centered", "product_type": "illustration"},
    ))
    monkeypatch.setattr(jobs, "make_thumb", lambda src, stem: "thumb.webp")
    monkeypatch.setattr(jobs._router, "LAST_MODEL", "test-model")
    try:
        res = jobs.extract_one("D:/tmp/bunga.png", filename="bunga.png")
        assert res["status"] == "ok"
        assert res["data"]["description"] == "Gambar bunga di atas meja."
        assert res["data"]["kind"] == "extract"
        assert res["data"]["style"] == "watercolor"
        assert res["data"]["asset_type"] == "illustration"
        assert res["data"]["composition"] == "centered"
        assert res["data"]["colors"] == ["pink", "green"]
        row = db.get_run(res["id"])
        assert row["source"] == "extract"
        assert row["model"] == "test-model"
    finally:
        db.DB_PATH = saved
