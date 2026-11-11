"""kwgen.constants - prompt, aturan marketplace, plafon keyword, spesifikasi JSON."""

from .config import max_keywords

MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".webp": "image/webp", ".gif": "image/gif", ".bmp": "image/bmp"}

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}

EXTRACT_PROMPT = """You analyze images that will be sold as digital products: clip art, illustrations, photos, printables, patterns, templates and mockups.
Reply with ONE JSON object and nothing else, using exactly these keys:
"description": ONE plain-text English paragraph of 55-85 words, US spelling. Describe only what is visible: the main subject, visible elements, dominant colors, how it looks, the background, any text copied exactly between quotes or "no text", and the overall mood.
"asset_type": exactly one of "photo", "illustration", "clip art", "3D render", "screenshot", "pattern", "mockup", "printable", or "" if unclear.
"style": 1-3 words describing the visual style, your own wording (e.g. "flat illustration", "soft watercolor").
"mood": a list of 1-3 short words for the feeling the image gives.
"tone": 1-3 words for the color temperature or overall tone.
"colors": a list of 1-3 dominant colors in plain words.
"lighting": exactly one of "soft", "studio", "natural", "flat", "dramatic" for photos and 3D renders only; "" for every other asset_type or if unclear.
"composition": exactly one of "centered", "flat lay", "close-up", "wide", "isometric", or "" if unclear.
"product_type": 1-3 words for what kind of digital product this image looks like.
Leave a field empty ("" or []) rather than guess. Never invent a value that is not visible.
Never name a brand, franchise, character, artist or real person, and never guess a file format or a technical medium such as vector, EPS or PNG.
If a watermark or logo is visible, say only that a watermark is present, never whose it is.
No markdown, no preamble, no questions, no marketing claims."""

SYSTEM_PROMPT = """You describe images that will be sold as digital products: clip art, illustrations, photos, printables, patterns, templates and mockups.
Write ONE plain-text paragraph of 55-85 words, in English only, using US spelling.
Order it like this: (1) what the product is - a single subject, a set or collection, a repeating pattern, a mockup or a printable - and how many items only when the count is obvious; (2) the main subject; (3) visible elements; (4) dominant colors; (5) how it looks - flat, hand-drawn, painted, photographic, 3D or textured; (6) the background: plain white, a full scene, a frame or border, or edge-to-edge; (7) any text that actually appears, copied exactly between quotes, or "no text"; (8) the overall mood.
Never name a brand, franchise, character, artist or real person, and never guess a file format or a technical medium such as vector, EPS or PNG - describe only how the image looks.
If a watermark or logo is visible, say only that a watermark is present, never whose it is.
No JSON, no markdown, no preamble, no questions, no marketing claims."""


# Plafon keras per marketplace menurut aturan platform. Angka ini TIDAK dipakai
# langsung: jumlah efektif selalu di-min-kan dengan `max_keywords()` di config,
# jadi satu pengaturan berlaku sama untuk semua marketplace.
KEYWORD_CAPS = {"etsy": 13, "canva": 20, "creative_market": 10,
                "universal": 30, "adobe": 49}


def cap_for(market):
    """Jumlah keyword efektif = plafon platform, dibatasi setting config."""
    return min(KEYWORD_CAPS[market], max_keywords())

# Aturan khusus per marketplace, disuntikkan hanya ke langkah yang relevan.
# Sumber: docs/riset-system-prompt.md
STEP_RULES = {
    # Etsy: exact-match menang, tag tidak boleh menduplikasi title, dan
    # bentuk tunggal/jamak sudah dinormalisasi mesin pencari.
    "etsy": "The first tag must be the hero phrase naming WHAT the product is "
            "(for example 'floral clip art' or 'flower illustration'), not a use case. "
            "Then cover product variations, gift occasions, recipient and use case. "
            "Tags must complement the title, not repeat its words.",
    # Adobe: urutan keyword menentukan ranking, 10 pertama paling berat.
    "adobe": "Order the keywords from most to least important; the first 10 decide most of the ranking. "
             "One concept per keyword (white, fluffy, puppy - not 'white fluffy puppy'). "
             "Include setting, mood and concept keywords, not only objects.",
}

# Urutan kartu di UI + langkah AI yang dibutuhkan tiap marketplace.
# Mencentang satu marketplace = 1 panggilan vision + N langkah di bawah.
ALL_MARKETS = ["etsy", "canva", "creative_market", "universal", "adobe"]
MARKET_STEPS = {
    "etsy": ["etsy"],
    "canva": ["canva"],
    "creative_market": ["creative_market", "style"],
    "universal": ["universal", "core"],
    "adobe": ["adobe"],
}


# Model gratis di 9router menolak membalas JSON besar (balas prosa/SVG).
# Strategi: deskripsi teks kecil -> 7 panggilan JSON kecil yang independen.
def SEO_SPECS(n=None):
    n = n or max_keywords()
    etsy_n = min(KEYWORD_CAPS["etsy"], n)
    canva_n = min(KEYWORD_CAPS["canva"], n)
    uni_n = min(KEYWORD_CAPS["universal"], n)
    adobe_n = min(KEYWORD_CAPS["adobe"], n)
    cm_n = min(KEYWORD_CAPS["creative_market"], n)
    return {
        "core": ('{"subject":"","elements":[],"medium":""}',
                 "the core subject, visible elements and visible medium"),
        "style": ('{"style":[],"colors":[],"use_cases":[]}',
                  "art style, color names and buyer use cases"),
        "etsy": (f'{{"tags":["t1",...,"t{etsy_n}"]}}',
                 f"EXACTLY {etsy_n} Etsy search tags",
                 "Write them in lowercase. Each tag must be a phrase of 2-5 words and at most 20 characters."),
        "canva": ('{"title":"...","tags":["..."],"alt_titles":["...","...","..."]}',
                  f"one keyword-rich Canva listing title (60-120 chars), {canva_n} tags, 3 alt titles",
                  "The title must say who the product is for, using words taken from THIS "
                  "image's own theme, room or use case - never a generic example phrase. "
                  "Include the file format only when the known file facts line states one; "
                  "never invent a format. If no format is known, use orientation or item "
                  "count instead when the visual description states it. Never write the words "
                  "'buyer', 'customer' or 'audience' in the title. "
                  "The 3 alt titles must differ in structure and ending - do not end "
                  "all of them with the same phrase."),
        "creative_market": ('{"title":"...","description":"...","tags":["..."]}',
                            "a clean Creative Market product title, a 3-sentence narrative description, "
                            f"and {cm_n} tags"),
        "universal": ('{"title":"...","tags":["..."]}',
                      f"one descriptive stock-photo title (60-100 chars) and {uni_n} English stock-image tags "
                      "for Freepik / Shutterstock and similar stock sites",
                      "The title must read like a caption, not a list of words."),
        "adobe": ('{"title":"...","tags":["..."]}',
                  "one Adobe Stock listing title (at most 200 chars, ideally under 70) "
                  f"and {adobe_n} English stock keywords"),
    }


# Aturan mutu yang berlaku di SEMUA marketplace (terbukti dari panduan resmi
# Adobe, Shutterstock, Etsy, Creative Market). Sengaja pendek & imperatif
# supaya model kecil/gratis tetap patuh.
SEO_RULES = (
    "Rules: all text in ENGLISH only, using US spelling. Write the words buyers actually type, "
    "never technical jargon. Only describe what the visual description and the known file facts "
    "support - never invent objects, properties, formats or counts. "
    "Use each keyword once: no duplicates, and no singular/plural pair of the same word "
    "(search engines already match both). "
    "Never include a file type unless the task explicitly asks for one and the known file facts "
    "line states it; never invent a format. Never add a property (seamless, transparent, vector, "
    "pattern, item count) unless the visual description or known file facts state it. "
    "Never include filler words (nice, cool, beautiful), promotional words (sale, discount, cheap, "
    "fast shipping), special characters, brands, franchises, artist names, or real people. "
    "Reply with the JSON object only - no markdown fence, no commentary."
)
