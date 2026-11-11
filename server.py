"""server.py — FastAPI untuk Image Keyword Generator v2 (web lokal).

Bind HANYA ke 127.0.0.1. Tanpa login, tanpa multiuser — ini tool personal.
Jalankan lewat app.py (yang juga membuka browser), bukan langsung.
Route tinggal di paket app_api/.
"""

import core  # noqa: F401  — memuat config saat startup
import db  # noqa: F401  — menyiapkan skema SQLite
import signals  # noqa: F401
from app_api import app  # noqa: F401

__all__ = ["app"]
