"""Self-check fitur Generate Gambar: validasi, panggilan endpoint, riwayat scope image."""

import tempfile
from pathlib import Path

import pytest

import db
import kwgen.image_gen as image_gen


def _temp_db():
    return Path(tempfile.mkdtemp()) / "history.db"


@pytest.fixture
def cfg(monkeypatch):
    monkeypatch.setitem(image_gen.CFG, "image_base_url", "https://ai.example.com/v1")
    monkeypatch.setitem(image_gen.CFG, "image_api_key", "gk-test")
    monkeypatch.setitem(image_gen.CFG, "image_model", "flux-2-flex")
    monkeypatch.setitem(image_gen.CFG, "image_size", "1024x1024")
    monkeypatch.setitem(image_gen.CFG, "timeout_seconds", 30)


class _Resp:
    def __init__(self, body):
        self.body = body

    def read(self, *_):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def test_images_url_normalize(cfg, monkeypatch):
    assert image_gen.images_url() == "https://ai.example.com/v1/images/generations"
    monkeypatch.setitem(image_gen.CFG, "image_base_url", "https://ai.example.com/v1/images/generations")
    assert image_gen.images_url() == "https://ai.example.com/v1/images/generations"


def test_generate_request_and_result(cfg, monkeypatch):
    seen = {}

    def fake_urlopen(req, timeout=None):
        seen["url"] = req.full_url
        seen["auth"] = req.get_header("Authorization")
        seen["body"] = req.data
        seen["timeout"] = timeout
        return _Resp(b'{"data":[{"url":"https://cdn.example.com/a.png"}]}')

    monkeypatch.setattr(image_gen.urllib.request, "urlopen", fake_urlopen)
    urls = image_gen.generate("kucing oranye", n=1, size=None)
    assert urls == ["https://cdn.example.com/a.png"]
    assert seen["url"] == "https://ai.example.com/v1/images/generations"
    assert seen["auth"] == "Bearer gk-test"
    assert seen["timeout"] == 30
    import json
    body = json.loads(seen["body"])
    assert body == {"model": "flux-2-flex", "prompt": "kucing oranye", "n": 1,
                    "size": "1024x1024", "response_format": "url"}


def test_generate_validation(cfg):
    with pytest.raises(ValueError):
        image_gen.generate("")
    with pytest.raises(ValueError):
        image_gen.generate("x" * 4001)
    with pytest.raises(ValueError):
        image_gen.generate("ok", n=5)
    with pytest.raises(ValueError):
        image_gen.generate("ok", size="999x999")


def test_generate_needs_config(monkeypatch):
    monkeypatch.setitem(image_gen.CFG, "image_base_url", "")
    monkeypatch.setitem(image_gen.CFG, "image_api_key", "gk-test")
    with pytest.raises(RuntimeError, match="Base URL"):
        image_gen.generate("ok")
    monkeypatch.setitem(image_gen.CFG, "image_base_url", "https://ai.example.com/v1")
    monkeypatch.setitem(image_gen.CFG, "image_api_key", "")
    with pytest.raises(RuntimeError, match="Kunci API"):
        image_gen.generate("ok")


def test_generate_empty_response(cfg, monkeypatch):
    monkeypatch.setattr(image_gen.urllib.request, "urlopen",
                        lambda req, timeout=None: _Resp(b'{"data":[]}'))
    with pytest.raises(RuntimeError, match="tidak berisi gambar"):
        image_gen.generate("ok")


def test_download(cfg, monkeypatch, tmp_path):
    monkeypatch.setattr(image_gen.urllib.request, "urlopen",
                        lambda url, timeout=None: _Resp(b"\x89PNGdata"))
    name = image_gen.download("https://cdn.example.com/a.webp?sig=1", tmp_path)
    assert name.endswith(".webp")
    assert (tmp_path / name).read_bytes() == b"\x89PNGdata"


def test_download_rejects_bad_scheme(tmp_path):
    with pytest.raises(RuntimeError):
        image_gen.download("file:///etc/passwd", tmp_path)


def test_image_one_saves_history(cfg, monkeypatch):
    import app_api.jobs as jobs

    saved = db.DB_PATH
    db.DB_PATH = _temp_db()
    db.init()
    monkeypatch.setattr(jobs.image_gen, "generate",
                        lambda prompt, n, size: ["https://cdn.example.com/a.png"])
    monkeypatch.setattr(jobs.image_gen, "download", lambda url, dest: "img_test.png")
    try:
        res = jobs.image_one("kucing oranye", n=1, size=None)
        assert res["status"] == "ok"
        assert res["data"]["images"] == ["img_test.png"]
        row = db.get_run(res["id"])
        assert row["source"] == "image"
        assert row["thumb"] == "img_test.png"
        rows, total = db.list_runs(scope="image")
        assert total == 1 and rows[0]["id"] == res["id"]
        assert db.list_runs(scope="keyword")[1] == 0
        assert db.list_runs(scope="extract")[1] == 0
    finally:
        db.DB_PATH = saved


def test_image_one_error_is_recorded(cfg, monkeypatch):
    import app_api.jobs as jobs

    saved = db.DB_PATH
    db.DB_PATH = _temp_db()
    db.init()

    def boom(prompt, n, size):
        raise RuntimeError("HTTP 402: saldo habis")

    monkeypatch.setattr(jobs.image_gen, "generate", boom)
    try:
        res = jobs.image_one("kucing", n=1, size=None)
        assert res["status"] == "error"
        row = db.get_run(res["id"])
        assert row["status"] == "error" and "saldo" in row["error"]
    finally:
        db.DB_PATH = saved
