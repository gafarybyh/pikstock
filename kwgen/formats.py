"""kwgen.formats - formatter teks per marketplace."""


def fmt_etsy(d):
    tags = [str(t).strip().lower() for t in d.get("etsy_tags", [])][:13]
    lines, warn = [], []
    for i, t in enumerate(tags, 1):
        bad = len(t) > 20
        if bad:
            warn.append(f"tag #{i} '{t}' = {len(t)} char (>20)")
        lines.append(f"{i:2}. {t:<22} ({len(t)})" + ("  <-- OVER LIMIT" if bad else ""))
    head = f"Etsy tags: {len(tags)}/13"
    if warn:
        head += "\nPERINGATAN:\n  " + "\n  ".join(warn)
    return head + "\n\n" + "\n".join(lines)


def fmt_canva(d):
    tags = ", ".join(d.get("canva_tags", []))
    alts = "\n".join(f"- {t}" for t in d.get("alt_titles", []))
    return (f"JUDUL:\n{d.get('canva_title','')}\n\n"
            f"TAGS ({len(d.get('canva_tags', []))}):\n{tags}\n\n"
            f"JUDUL ALTERNATIF:\n{alts}")


def fmt_creative_market(d):
    tags = d.get("creative_market_tags", [])
    return (f"JUDUL:\n{d.get('creative_market_title','')}\n\n"
            f"TAGS ({len(tags)}):\n" + ", ".join(tags) + "\n\n"
            f"DESKRIPSI:\n{d.get('creative_market_description','')}\n\n"
            f"STYLE: {', '.join(d.get('style', []))}\n"
            f"USE CASES: {', '.join(d.get('use_cases', []))}")


def fmt_universal(d):
    return (f"JUDUL:\n{d.get('universal_title','')}\n\n"
            f"SUBJECT: {d.get('subject','')}\n"
            f"MEDIUM: {d.get('medium','')}\n\n"
            f"TAGS ({len(d.get('universal_tags', []))}):\n"
            + ", ".join(d.get("universal_tags", [])))


def fmt_adobe(d):
    tags = d.get("adobe_tags", [])
    return (f"JUDUL:\n{d.get('adobe_title','')}\n\n"
            f"KEYWORDS ({len(tags)}):\n" + ", ".join(tags))


def fmt_all(d):
    """Semua marketplace jadi satu teks - untuk tombol 'Copy semua' / export TXT."""
    return (f"### ETSY ###\n{fmt_etsy(d)}\n\n### CANVA ###\n{fmt_canva(d)}\n\n"
            f"### CREATIVE MARKET ###\n{fmt_creative_market(d)}\n\n"
            f"### UNIVERSAL ###\n{fmt_universal(d)}\n\n"
            f"### ADOBE STOCK ###\n{fmt_adobe(d)}\n")
