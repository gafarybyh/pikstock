"""Self-check murni (tanpa jaringan): klasifikasi sinyal + baris CSV.

Jalankan:  python -m pytest -q test/test_signals.py
"""
import core
import signals


def test_classify():
    assert signals.classify("flower clipart", ["flower clipart", "flower clipart png"], []) == ("kuat", 0)
    assert signals.classify("flower clipart", ["x", "flower clipart"], []) == ("kuat", 1)
    assert signals.classify("flower clipart", ["flower clipart png", "flower clipart bw"], []) == ("sedang", -1)
    assert signals.classify("potted flower clipart", ["potted flower pink"], ["potted flower", "potted flowers"]) == ("sedang", -1)
    assert signals.classify("xyzzy nonsense", ["something else"], ["xyzzy"]) == ("lemah", -1)
    assert signals.classify("", [], []) == ("lemah", -1)
    print("classify OK")


def test_max_signal_terms():
    """Batas keyword cek sinyal: default 150, clamp 20-500, tahan nilai rusak."""
    saved = dict(core.CFG)
    try:
        core.CFG["max_signal_terms"] = 150
        assert core.max_signal_terms() == 150
        core.CFG["max_signal_terms"] = 9999
        assert core.max_signal_terms() == 500, "clamp atas"
        core.CFG["max_signal_terms"] = 1
        assert core.max_signal_terms() == 20, "clamp bawah"
        core.CFG["max_signal_terms"] = "abc"
        assert core.max_signal_terms() == 150, "nilai rusak -> default"
    finally:
        core.CFG.clear()
        core.CFG.update(saved)
    print("max_signal_terms OK")


def test_csv_rows():
    data = {"subject": "flower", "elements": ["leaf", "  ", ""], "medium": "vector",
            "style": ["flat"], "colors": ["pastel pink"], "use_cases": ["wedding invite"],
            "etsy_tags": ["flower clipart", "floral png", "floral png"],
            "canva_title": "Flower Clipart Set", "canva_tags": ["floral"], "alt_titles": ["Alt 1"],
            "creative_market_title": "CM Title", "creative_market_description": "Desc.",
            "universal_tags": ["floral", "botanical"]}
    rows = core.csv_rows(data, 7, "f.png", "2026-01-01T00:00:00")
    assert rows, "harus ada baris"
    assert all(len(r) == len(core.CSV_HEADER) for r in rows), "lebar kolom konsisten"
    assert all(r[5] for r in rows), "tidak ada value kosong"
    flat = [r[3:] for r in rows]
    assert ("etsy", "tag", "floral png") in flat
    assert ("core", "element", "leaf") in flat
    assert ("canva", "alt_title", "Alt 1") in flat
    assert ("creative_market", "description", "Desc.") in flat
    print(f"csv_rows OK ({len(rows)} baris)")


if __name__ == "__main__":
    test_classify()
    test_max_signal_terms()
    test_csv_rows()
    print("SEMUA OK")
