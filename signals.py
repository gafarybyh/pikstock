"""signals.py — sinyal demand lintas-market via Google Suggest. Bebas UI.

Suggest = kata yang benar-benar diketik orang. Gratis, tanpa key, berlaku
untuk semua marketplace (bukan hanya Etsy). Gagal jaringan / endpoint berubah
-> status 'n/a', bukan error (degradasi anggun). Hasil di-cache di tabel
signal (TTL 7 hari) supaya tidak memanggil Google berulang.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

import db

SUGGEST_URL = "https://suggestqueries.google.com/complete/search?client=firefox&q="
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")
TTL_DAYS = 7


class SuggestError(Exception):
    """Endpoint suggest tidak bisa dihubungi / balasan tidak dikenal."""


def google_suggest(term, timeout=8):
    """-> list saran (str). Raise SuggestError kalau endpoint tidak terjangkau."""
    q = urllib.parse.quote(str(term).strip())
    req = urllib.request.Request(SUGGEST_URL + q, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = json.loads(r.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise SuggestError(str(e)) from e
    if isinstance(raw, list) and len(raw) > 1 and isinstance(raw[1], list):
        return [str(s) for s in raw[1]]
    raise SuggestError("bentuk balasan tidak dikenal")


def classify(term, suggestions, head_suggestions=()):
    """Pure. Tentukan status demand dari dua daftar saran.

    kuat   = term muncul persis di saran
    sedang = term adalah awalan saran (long-tail lebih panjang), atau
             kata-kata awal term memang diketik orang (ada di saran head)
    lemah  = tidak ada jejak sama sekali
    -> (status, pos); pos = indeks 0-based saat exact, -1 selain itu.
    """
    t = str(term).lower().strip()
    if not t:
        return "lemah", -1
    for i, s in enumerate(suggestions):
        if str(s).lower().strip() == t:
            return "kuat", i
    for s in suggestions:
        if str(s).lower().strip().startswith(t):
            return "sedang", -1
    head = " ".join(t.split()[:2])
    for s in head_suggestions:
        if str(s).lower().strip() == head:
            return "sedang", -1
    return "lemah", -1


def score_term(term):
    """Satu term -> dict status (dengan cache). Tidak pernah raise."""
    term = str(term).strip()
    if not term:
        return {"term": "", "status": "lemah", "pos": -1, "note": "kosong", "cached": False}
    cached = db.get_signal(term, TTL_DAYS)
    if cached:
        cached["cached"] = True
        return cached

    head = " ".join(term.lower().split()[:2])
    try:
        suggestions = google_suggest(term)
        status, pos = classify(term, suggestions, [])
        if status == "lemah" and head != term.lower():
            # Head hanya bisa mengubah hasil saat term tak punya jejak sama
            # sekali. Cek dulu hasilnya; jangan boros query tiap kali.
            status, pos = classify(term, suggestions, google_suggest(head))
    except SuggestError as e:
        return {"term": term, "status": "n/a", "pos": -1,
                "note": "tidak bisa menghubungi Google: " + str(e), "cached": False}
    note = {"kuat": "muncul persis di saran Google",
            "sedang": "muncul sebagai variasi di saran Google",
            "lemah": "tidak muncul di saran Google"}[status]
    db.set_signal(term, status, pos, note)
    return {"term": term, "status": status, "pos": pos, "note": note, "cached": False}
