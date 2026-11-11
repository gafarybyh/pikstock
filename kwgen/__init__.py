"""kwgen - logika keyword generator, BEBAS UI.

Dipakai oleh keyword_gen.py (GUI tkinter lama), server.py (web v2), dan app_api/.
Tidak boleh import tkinter / web framework apa pun.

Paket ini dipecah dari core.py tanpa mengubah perilaku:
    config      config.json read/save/reload, CFG, MODELS, max_keywords, max_signal_terms
    constants   prompt & aturan marketplace, plafon keyword, spesifikasi JSON
    imaging     encode image -> base64 (downscale bila PIL tersedia)
    router      panggilan HTTP ke router AI + fallback model (LAST_MODEL)
    parsing     parse_json / penutup JSON terpotong
    text        fit_tag, filter tag/judul, quality_warnings
    urls        buang URL dari teks (dipakai signals.clean_head)
    pipeline    build_keywords (vision -> langkah JSON per marketplace)
    formats     formatter per marketplace + fmt_all
    csvio       CSV_HEADER + csv_rows
    outputs     save_outputs (tmp/*.json + tmp/*.txt)

`core.py` di root me-re-export semua nama di atas, jadi pemanggil lama tetap jalan.
"""

from .config import (
    BASE,
    CFG,
    CONFIG_LOCK,
    CONFIG_PATH,
    MODELS,
    max_keywords,
    max_signal_terms,
    read_config,
    reload_config,
    save_config,
)
from .constants import (
    ALL_MARKETS,
    IMAGE_EXTS,
    KEYWORD_CAPS,
    MARKET_STEPS,
    MIME,
    SEO_RULES,
    SEO_SPECS,
    STEP_RULES,
    SYSTEM_PROMPT,
    cap_for,
)
from .csvio import CSV_HEADER, csv_rows
from .formats import (
    fmt_adobe,
    fmt_all,
    fmt_canva,
    fmt_creative_market,
    fmt_etsy,
    fmt_universal,
)
from .imaging import HAVE_PIL, encode_image
from .outputs import save_outputs
from .parsing import parse_json
from .pipeline import build_keywords, call_vision, extract_describe, seo_step
from .router import LAST_MODEL, api_key
from .text import (
    BANNED,
    BANNED_TAGS,
    BANNED_WORDS,
    MIN_TAGS,
    TITLE_STOPWORDS,
    fit_tag,
    quality_warnings,
)
from .urls import strip_urls

__all__ = [
    "ALL_MARKETS",
    "BASE",
    "BANNED",
    "BANNED_TAGS",
    "BANNED_WORDS",
    "CFG",
    "CONFIG_LOCK",
    "CONFIG_PATH",
    "CSV_HEADER",
    "HAVE_PIL",
    "IMAGE_EXTS",
    "KEYWORD_CAPS",
    "LAST_MODEL",
    "MARKET_STEPS",
    "MIN_TAGS",
    "MIME",
    "MODELS",
    "SEO_RULES",
    "SEO_SPECS",
    "STEP_RULES",
    "SYSTEM_PROMPT",
    "TITLE_STOPWORDS",
    "api_key",
    "build_keywords",
    "call_vision",
    "cap_for",
    "csv_rows",
    "encode_image",
    "extract_describe",
    "fit_tag",
    "fmt_adobe",
    "fmt_all",
    "fmt_canva",
    "fmt_creative_market",
    "fmt_etsy",
    "fmt_universal",
    "max_keywords",
    "max_signal_terms",
    "parse_json",
    "quality_warnings",
    "read_config",
    "reload_config",
    "save_config",
    "save_outputs",
    "seo_step",
    "strip_urls",
]
