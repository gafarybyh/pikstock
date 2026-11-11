"""kwgen.outputs - simpan hasil satu gambar ke tmp/ (JSON + TXT)."""

import json
from pathlib import Path

from .config import BASE, CFG
from .formats import fmt_all


def save_outputs(path, data):
    """Simpan JSON + TXT ke tmp/ (dipakai GUI lama dan web)."""
    out = BASE / CFG.get("temp_dir", "tmp")
    out.mkdir(exist_ok=True)
    stem = Path(path).stem
    (out / f"{stem}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / f"{stem}.txt").write_text(fmt_all(data), encoding="utf-8")
    return out
