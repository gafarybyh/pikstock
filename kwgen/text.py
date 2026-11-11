"""kwgen.text - normalisasi tag & judul, peringatan mutu per marketplace."""

import re


def fit_tag(tag, limit=20):
    """Potong di batas kata, jangan pernah menghasilkan 'clipar'."""
    t = str(tag).lower().strip()
    if len(t) <= limit:
        return t
    cut = t[:limit]
    if t[limit] != " ":  # terpotong di tengah kata -> mundur ke spasi terakhir
        cut = cut.rsplit(" ", 1)[0] if " " in cut else cut
    return cut.strip() or t[:limit]


# Tag yang isinya PERSIS kata di bawah ini dibuang seluruhnya.
BANNED_TAGS = {
    "sale", "discount", "cheap", "free", "best price", "fast shipping",
    "nice", "cool", "beautiful", "amazing", "pretty", "lovely", "cute",
    "eps", "eps10", "jpg", "jpeg", "png", "psd", "svg", "ai", "pdf",
}

# Kata di bawah ini membuat SELURUH tag dibuang walau hanya muncul sebagai
# salah satu kata ("spring sale graphic", "svg file", "eps10 vector").
# Sengaja hanya tipe file + kata promosi: kata rasa seperti "cute" atau
# "pretty" justru dicari pembeli ("cute flower pot"), jadi tidak masuk sini.
BANNED_WORDS = {
    "eps", "eps10", "svg", "png", "jpg", "jpeg", "psd", "pdf", "tiff",
    "sale", "discount", "cheap", "free", "clearance", "promo", "bestseller",
    "vecteezy", "freepik", "shutterstock", "adobe", "canva", "etsy",
    "envato", "creativemarket", "dreamstime", "istock", "getty", "photoshop",
}

BANNED_PHRASES = {
    "creative market", "adobe stock", "getty images", "istock photo",
}

# Dipertahankan supaya kode lama yang mengimpor `BANNED` tetap jalan.
BANNED = BANNED_TAGS

_BRAND_RE = re.compile(
    r"\b(?:vecteezy|freepik|shutterstock|adobe(?:\s+stock)?|photoshop|canva|etsy|envato|"
    r"creativemarket|creative\s+market|dreamstime|istock|getty\s+images)\b",
    re.I,
)

_US_SPELLING = {
    "colour": "color", "colours": "colors", "coloured": "colored",
    "colourful": "colorful", "watercolour": "watercolor",
    "watercolours": "watercolors", "grey": "gray", "greys": "grays",
    "jewellery": "jewelry", "jewellry": "jewelry", "centre": "center",
    "centres": "centers", "fibre": "fiber", "metre": "meter",
    "theatre": "theater", "organise": "organize", "organised": "organized",
    "realise": "realize", "realised": "realized", "favourite": "favorite",
    "favourites": "favorites", "personalised": "personalized",
    "customised": "customized", "optimise": "optimize",
}

_US_RE = re.compile(r"\b(" + "|".join(map(re.escape, _US_SPELLING)) + r")\b", re.I)


def _us_word(match):
    word = match.group(0)
    replacement = _US_SPELLING.get(word.lower())
    if not replacement:
        return word
    if word.isupper():
        return replacement.upper()
    if word[0].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def _us_spelling(text):
    return _US_RE.sub(_us_word, str(text or ""))


def _clean_desc(text):
    t = _BRAND_RE.sub("", str(text or ""))
    t = _us_spelling(t)
    t = re.sub(r"\bwatermark\s+watermark\b", "watermark", t, flags=re.I)
    return re.sub(r"\s{2,}", " ", t).strip()


def _clean_tags(tags, cap, max_len=0):
    """Normalisasi + buang duplikat/plural/filler, lalu potong ke `cap`.

    Dedupe memakai kata dasar yang diurutkan, jadi "flower" dan "flowers"
    dihitung sama (mesin pencari sudah mencocokkan keduanya).
    """
    out, seen = [], set()
    for raw in tags or []:
        if raw is None:
            continue
        t = _us_spelling(str(raw).lower().strip().strip(".,;:-"))
        if not t or t in BANNED_TAGS or not any(ch.isalpha() for ch in t):
            continue  # kosong, filler, atau tag tanpa huruf (mis. "123")
        if any(phrase in t for phrase in BANNED_PHRASES):
            continue  # nama brand multi-kata
        words = t.split()
        if BANNED_WORDS.intersection(words):
            continue  # tipe file / kata promosi / brand di dalam frasa
        if max_len:
            t = fit_tag(t, max_len)
        if not t:
            continue
        k = " ".join(sorted(w.rstrip("s") for w in t.split()))
        if k in seen:
            continue
        seen.add(k)
        out.append(t)
        if len(out) >= cap:
            break
    return out


# Kata yang tidak boleh muncul di judul karena kedengaran seperti mesin,
# bukan seperti penjual manusia ("art for home decor buyers").
TITLE_STOPWORDS = {"buyers", "buyer", "customers", "customer", "audience"}

# Kata sambung yang jadi menggantung setelah stopword di atas dibuang
# ("art for buyers" -> "art for" -> "art").
_CONNECTORS = {"for", "and", "with", "in", "of", "the", "a", "an", "to", "by",
               "on", "or", "from", "at"}


def _clean_title(title):
    """Rapikan judul: buang brand, ejaan UK, kata 'buyer/customer' + sambung."""
    text = _us_spelling(_BRAND_RE.sub("", str(title or "")))
    words = [w for w in text.split()
             if w.lower().strip(".,;:") not in TITLE_STOPWORDS]
    # Buang sambung berurutan di tengah ("for and" -> "for").
    i = 0
    while i < len(words) - 1:
        if (words[i].lower() in _CONNECTORS
                and words[i + 1].lower() in _CONNECTORS):
            del words[i + 1]
        else:
            i += 1
    # Buang sambung di ujung kalimat.
    while words and words[-1].lower().strip(".,;:") in _CONNECTORS:
        words.pop()
    while words and words[0].lower().strip(".,;:") in _CONNECTORS:
        words.pop(0)
    if not words:
        return ""
    t = " ".join(words)
    return t[0].upper() + t[1:]  # judul selalu berhuruf besar di awal


def _clean_titles(titles):
    """Versi `_clean_title` untuk daftar; buang yang jadi kosong & duplikat."""
    out, seen = [], set()
    for raw in titles or []:
        t = _clean_title(raw)
        k = t.lower()
        if t and k not in seen:
            seen.add(k)
            out.append(t)
    return out


# Batas minimal yang membuat listing masih punya peluang tampil.
MIN_TAGS = {"etsy": 13, "canva": 10, "creative_market": 5, "universal": 15, "adobe": 15}


def quality_warnings(data):
    """Cek hasil terhadap batas platform - dilaporkan, tidak membatalkan hasil."""
    warn = []
    picked = data.get("_marketplaces")
    for market, field in (("etsy", "etsy_tags"), ("canva", "canva_tags"),
                          ("creative_market", "creative_market_tags"),
                          ("universal", "universal_tags"), ("adobe", "adobe_tags")):
        if picked is not None and market not in picked:
            continue  # marketplace tidak dipilih -> wajar kosong
        n = len(data.get(field) or [])
        need = MIN_TAGS[market]
        if n < need:
            warn.append(f"{market}: {n} tag (disarankan >= {need})")
    if data.get("universal_tags") and not data.get("universal_title"):
        warn.append("universal: title kosong (bobotnya lebih besar dari tag)")
    return warn
