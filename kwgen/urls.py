"""kwgen.urls - bersihkan URL dari teks (dipakai signals.clean_head)."""


def strip_urls(text):
    """Buang semua URL dari teks sebelum dikirim ke Google Suggest."""
    raw = text.replace("/", " ")
    dropped = {"http:", "https:", "www.", "www"}
    return " ".join(w for w in raw.split() if w.lower() not in dropped)
