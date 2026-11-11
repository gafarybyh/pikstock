"""kwgen.csvio - hasil satu run dijadikan baris CSV datar."""

CSV_HEADER = ("run_id", "filename", "created_at", "marketplace", "type", "value")


def csv_rows(data, run_id="", filename="", created_at=""):
    """Datar-kan satu hasil menjadi baris (marketplace, type, value) untuk CSV.

    Nilai kosong dibuang. Duplikat dibiarkan - pasar yang bisa membedakan
    tetap urusan pemakai CSV.
    """
    rows = []

    def add(market, kind, value):
        v = str(value or "").strip()
        if v:
            rows.append((run_id, filename, created_at, market, kind, v))

    d = data or {}
    add("core", "subject", d.get("subject"))
    add("core", "medium", d.get("medium"))
    for e in d.get("elements") or []:
        add("core", "element", e)
    for s in d.get("style") or []:
        add("style", "style", s)
    for c in d.get("colors") or []:
        add("style", "color", c)
    for u in d.get("use_cases") or []:
        add("style", "use_case", u)
    for t in d.get("etsy_tags") or []:
        add("etsy", "tag", t)
    add("canva", "title", d.get("canva_title"))
    for t in d.get("canva_tags") or []:
        add("canva", "tag", t)
    for t in d.get("alt_titles") or []:
        add("canva", "alt_title", t)
    add("creative_market", "title", d.get("creative_market_title"))
    add("creative_market", "description", d.get("creative_market_description"))
    for t in d.get("creative_market_tags") or []:
        add("creative_market", "tag", t)
    add("universal", "title", d.get("universal_title"))
    for t in d.get("universal_tags") or []:
        add("universal", "tag", t)
    add("adobe", "title", d.get("adobe_title"))
    for t in d.get("adobe_tags") or []:
        add("adobe", "tag", t)
    return rows
