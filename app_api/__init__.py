"""app_api — paket router FastAPI untuk Image Keyword Generator.

server.py tinggal import paket ini; urutan import menentukan urutan registrasi
route dan mount static.
"""

from . import (
    routes_config,  # noqa: F401
    routes_extract,  # noqa: F401
    routes_history,  # noqa: F401
    routes_image,  # noqa: F401
    routes_jobs,  # noqa: F401
    routes_pick,  # noqa: F401
    routes_signals,  # noqa: F401
    routes_static,  # noqa: F401
)
from .context import app

__all__ = ["app"]
