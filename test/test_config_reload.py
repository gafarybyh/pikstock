"""Self-check: perubahan config harus terlihat oleh modul yang mengimpor CFG/MODELS.

Jalankan:  python -m pytest -q test/test_config_reload.py
"""
import core
import kwgen.config as config
import kwgen.router as router


def test_reload_visible_without_restart():
    assert router.CFG is config.CFG
    assert router.MODELS is config.MODELS
    assert core.CFG is config.CFG
    assert core.MODELS is config.MODELS

    saved = config.read_config()
    try:
        config._apply_config({**saved, "model": "__probe__", "fallback_models": ["__fb__"]})
        assert router.MODELS == ["__probe__", "__fb__"]
        assert router.CFG["model"] == "__probe__"
        assert core.MODELS[0] == "__probe__"
        assert config._apply_config({**saved, "model": "__probe2__", "fallback_models": []})["model"] == "__probe2__"
        assert router.MODELS == ["__probe2__"]
    finally:
        config._apply_config(saved)
