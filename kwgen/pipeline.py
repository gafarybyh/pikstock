"""kwgen.pipeline - vision -> deskripsi, lalu langkah JSON per marketplace."""

import re

from . import router as _router
from .config import max_keywords
from .constants import (
    ALL_MARKETS,
    EXTRACT_PROMPT,
    MARKET_STEPS,
    SEO_RULES,
    SEO_SPECS,
    STEP_RULES,
    SYSTEM_PROMPT,
    cap_for,
)
from .imaging import encode_image_meta
from .parsing import parse_json
from .router import _post
from .text import _clean_desc, _clean_tags, _clean_title, _clean_titles, quality_warnings

MIN_DESC_WORDS = 50
MAX_DESC_WORDS = 95

_PREAMBLE_RE = re.compile(
    r"^\s*(?:here|sure|of course|this image|the image|i see|i can see|below|as an ai)\b",
    re.I,
)
_TECH_RE = re.compile(r"\b(?:vector|eps|eps10|png|jpe?g|psd|svg|tiff|pdf|raster)\b", re.I)

_FACT_FORMAT = {"canva"}
_FACT_SIZE = {"canva", "creative_market"}
_FACT_ORIENTATION = {"canva", "creative_market", "universal", "adobe"}
_FACT_ALPHA = {"etsy", "canva", "creative_market", "universal", "adobe"}


def _desc_issues(desc):
    text = str(desc or "").strip()
    words = text.split()
    n = len(words)
    issues = []
    if n < MIN_DESC_WORDS or n > MAX_DESC_WORDS:
        issues.append(f"{n} kata (target 55-85)")
    if not text:
        issues.append("deskripsi kosong")
    if "\n" in text:
        issues.append("lebih dari satu baris")
    if "{" in text or "}" in text:
        issues.append("mengandung JSON")
    if "`" in text or text.startswith("#"):
        issues.append("mengandung markdown")
    if text.endswith("?"):
        issues.append("berupa pertanyaan")
    if _PREAMBLE_RE.match(text):
        issues.append("ada preamble")
    if _TECH_RE.search(text):
        issues.append("menyebut format/medium teknis")
    letters = [c for c in text if c.isalpha()]
    ascii_letters = [c for c in letters if c.isascii()]
    if letters and len(ascii_letters) / len(letters) < 0.9:
        issues.append("bukan teks English")
    return issues


def _vision(path):
    mime, b64, meta = encode_image_meta(path)

    def payload(user_text):
        return {
            "max_tokens": 400,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": user_text},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                ]},
            ],
        }

    desc = _clean_desc(str(_post(payload("Describe this image."))).strip())
    issues = _desc_issues(desc)
    if issues:
        retry_text = (
            "Describe this image again. Your previous answer was rejected. "
            "Reply with ONE plain-text English paragraph of 55-85 words. "
            "Start with the main subject; describe only visible facts; never name "
            "a brand, watermark owner, file format or technical medium."
        )
        try:
            retry = _clean_desc(str(_post(payload(retry_text))).strip())
        except Exception:
            retry = ""
        if retry and len(_desc_issues(retry)) < len(issues):
            desc = retry
    if not desc:
        raise ValueError("Model tidak memberikan deskripsi gambar.")
    return desc, meta


def call_vision(path):
    return _vision(path)[0]


def _text(value, limit=40):
    if isinstance(value, list):
        value = value[0] if value else ""
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()[:limit]


def _texts(values, limit=3):
    if isinstance(values, str):
        values = [values]
    out = []
    for v in values or []:
        t = _text(v)
        if t and t not in out:
            out.append(t)
    return out[:limit]


def extract_describe(path):
    """Satu panggilan vision -> deskripsi + atribut dari daftar tetap."""
    mime, b64, _meta = encode_image_meta(path)
    raw = _post({
        "max_tokens": 600,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": EXTRACT_PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": "Analyze this image and reply with the JSON object."},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ]},
        ],
    })
    try:
        obj = parse_json(str(raw))
    except ValueError:
        obj = {"description": str(raw)}
    desc = _clean_desc(str(obj.get("description") or "").strip())
    if not desc:
        raise ValueError("Model tidak memberikan deskripsi gambar.")
    attrs = {
        "asset_type": _text(obj.get("asset_type")),
        "style": _text(obj.get("style")),
        "mood": _texts(obj.get("mood"), limit=2),
        "tone": _text(obj.get("tone")),
        "colors": _texts(obj.get("colors")),
        "lighting": _text(obj.get("lighting")),
        "composition": _text(obj.get("composition")),
        "product_type": _text(obj.get("product_type")),
    }
    return desc, attrs


def _format_label(meta):
    meta = meta or {}
    ext = str(meta.get("ext") or "").lower()
    return {"jpg": "JPG", "jpeg": "JPG"}.get(ext, str(meta.get("format") or "").upper())


def _ensure_format(title, meta):
    label = _format_label(meta)
    if not label:
        return title
    formats = {label, str((meta or {}).get("format") or "")}
    if any(f and re.search(rf"\b{re.escape(f)}\b", title, re.I) for f in formats):
        return title
    return f"{title} - {label}".strip(" -")


def _facts_for(key, meta):
    meta = meta or {}
    parts = []
    if key in _FACT_FORMAT:
        label = _format_label(meta)
        if label:
            parts.append(f"format {label}")
    if key in _FACT_SIZE and meta.get("width") and meta.get("height"):
        parts.append(f"{meta['width']}x{meta['height']} pixels")
    if key in _FACT_ORIENTATION and meta.get("orientation"):
        parts.append(f"{meta['orientation']} orientation")
    if key in _FACT_ALPHA:
        if meta.get("alpha") is True:
            parts.append("contains transparent pixels")
        elif meta.get("alpha") is False:
            parts.append("alpha channel is fully opaque")
    if not parts:
        return ""
    return ("Known file facts: " + ", ".join(parts) + ". "
            "Use them only when relevant; never invent beyond this line.")


def seo_step(desc, key, spec, facts=""):
    shape, task, *extra = spec
    # Susun perintah tanpa titik ganda: gabung bagian, tiap bagian satu titik.
    parts = [f"Write {task}"]
    parts += [e.strip().rstrip(".") for e in extra if e.strip()]
    special = STEP_RULES.get(key)
    if special:
        parts.append(special.strip().rstrip("."))
    body = ". ".join(parts) + "."
    prompt = f"Visual description of a digital product image:\n{desc}\n\n"
    if facts:
        prompt += f"{facts}\n\n"
    prompt += (f"{body}\nReturn this JSON shape exactly: {shape}\n"
               + SEO_RULES)
    return parse_json(_post({"max_tokens": 1600,
                             "messages": [{"role": "user", "content": prompt}]}))


def build_keywords(path, on_step=None, only=None):
    """Tahap 1 vision -> deskripsi; tahap 2 -> langkah JSON per marketplace.

    on_step: callback opsional (label:str) untuk progres di UI.
    only: daftar marketplace terpilih (mis. ["etsy", "canva"]). None = semua.
          Hanya langkah yang dibutuhkan pasar terpilih yang dijalankan,
          supaya panggilan AI tidak berlebihan.
    """
    def step(label):
        if on_step:
            try:
                on_step(label)
            except Exception:
                pass

    step("Membaca gambar")
    desc, meta = _vision(path)
    desc_issues = _desc_issues(desc)
    limit = max_keywords()
    specs = SEO_SPECS(limit)
    errors = []

    picked = ALL_MARKETS if only is None else [m for m in ALL_MARKETS if m in set(only)]
    wanted = {s for m in picked for s in MARKET_STEPS[m]}

    def need(key):
        if key not in wanted:  # pasar tidak dipilih -> tidak ada panggilan AI
            return {}
        step(f"Menulis {key}")
        try:
            return seo_step(desc, key, specs[key], facts=_facts_for(key, meta))
        except Exception as e:  # satu bagian gagal tidak membatalkan seluruh hasil
            errors.append(f"{key}: {e}")
            return {}

    core, style = need("core"), need("style")
    etsy, canva = need("etsy"), need("canva")
    cm, uni, adobe = need("creative_market"), need("universal"), need("adobe")
    canva_title = _ensure_format(_clean_title(canva.get("title", "")), meta)

    data = {
        "subject": core.get("subject", ""),
        "elements": core.get("elements", []),
        "medium": core.get("medium", ""),
        "style": style.get("style", []),
        "colors": style.get("colors", []),
        "use_cases": style.get("use_cases", []),
        "etsy_tags": _clean_tags(etsy.get("tags", []), cap=cap_for("etsy"), max_len=20),
        "canva_title": canva_title,
        "canva_tags": _clean_tags(canva.get("tags", []), cap=cap_for("canva")),
        "alt_titles": _clean_titles(canva.get("alt_titles")),
        "creative_market_title": _clean_title(cm.get("title", "")),
        "creative_market_description": _clean_desc(cm.get("description", "")),
        "creative_market_tags": _clean_tags(cm.get("tags", []), cap=cap_for("creative_market")),
        "universal_title": _clean_title(uni.get("title", "")),
        "universal_tags": _clean_tags(uni.get("tags", []), cap=cap_for("universal")),
        "adobe_title": _clean_title(adobe.get("title", "")),
        "adobe_tags": _clean_tags(adobe.get("tags", []), cap=cap_for("adobe")),
        "description": desc,
        "model": _router.LAST_MODEL,
    }
    if only is not None:
        data["_marketplaces"] = picked
    if errors:
        data["_errors"] = errors
    warn = [f"deskripsi: {x}" for x in desc_issues] + quality_warnings(data)
    if warn:
        data["_warnings"] = warn
    return data
