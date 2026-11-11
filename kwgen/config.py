"""kwgen.config - config.json, CFG, MODELS, batas keyword/sinyal."""

import json
import os
import threading
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE / "config.json"
CONFIG_LOCK = threading.RLock()


def _normalize_router(url):
    """Terima base URL (".../v1") maupun full endpoint (".../v1/chat/completions")."""
    u = str(url or "").strip().rstrip("/")
    return u if u.endswith("/chat/completions") else u + "/chat/completions"


def read_config():
    """Baca config.json apa adanya (tanpa normalisasi) - untuk UI pengaturan."""
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _apply_config(raw):
    cfg = dict(raw)
    cfg["router_url"] = _normalize_router(cfg.get("router_url", ""))
    models = [m for m in ([cfg.get("model")] + list(cfg.get("fallback_models") or [])) if m]
    CFG.clear()
    CFG.update(cfg)
    MODELS[:] = models
    return CFG


CFG: dict = {}
MODELS: list = []
_apply_config(read_config())


def reload_config():
    """Muat ulang config.json dan perbarui CFG/MODELS di tempat - berlaku tanpa restart."""
    with CONFIG_LOCK:
        return _apply_config(read_config())


def save_config(updates):
    """Gabung updates ke config.json secara atomik (key lain dipertahankan), lalu reload."""
    with CONFIG_LOCK:
        raw = read_config()
        raw.update(updates)
        tmp = CONFIG_PATH.with_name(CONFIG_PATH.name + ".tmp")
        tmp.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, CONFIG_PATH)
        return _apply_config(raw)


def max_keywords():
    """Batas atas jumlah keyword per marketplace (5-30, default 30 = tanpa potong)."""
    try:
        n = int(CFG.get("max_keywords", 30))
    except (TypeError, ValueError):
        n = 30
    return max(5, min(30, n))


def max_signal_terms():
    """Batas atas jumlah keyword untuk "Cek sinyal" (20-500, default 150).

    Maksimum teoretis seluruh marketplace = 13+20+10+30+30 = 103, jadi default
    150 sudah menampung semuanya. Angka ini hanya jaring aman.
    """
    try:
        n = int(CFG.get("max_signal_terms", 150))
    except (TypeError, ValueError):
        n = 150
    return max(20, min(500, n))
