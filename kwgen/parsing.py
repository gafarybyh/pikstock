"""kwgen.parsing - ambil JSON dari balasan model, termasuk yang terpotong."""

import json


def _close_truncated(t):
    """Tutup JSON yang terpotong di tengah (model kehabisan max_tokens).

    Kalau terpotong di dalam string, buang string setengah jadi itu
    (mis. "shape c) supaya tidak ada tag sampah di hasil akhir.
    """
    # 1. Buang ekor yang terpotong di tengah string.
    in_str = esc = False
    last_sep = -1
    for i, ch in enumerate(t):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch in "{[,":
            last_sep = i
    if in_str and last_sep >= 0:
        t = t[:last_sep + 1]
    t = t.rstrip().rstrip(",")

    # 2. Tutup kurung/kurawal yang masih terbuka.
    stack, in_str, esc = [], False, False
    for ch in t:
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch in "{[":
            stack.append(ch)
        elif ch in "}]" and stack:
            stack.pop()
    for ch in reversed(stack):
        t += "}" if ch == "{" else "]"
    return t


def parse_json(text):
    t = text.strip()
    if t.startswith("```"):
        t = t.split("```")[1]
        if t.lower().startswith("json"):
            t = t[4:]
    start = t.find("{")
    if start == -1:
        raise ValueError(f"Model tidak mengembalikan JSON:\n{text[:400]}")
    t = t[start:]
    end = t.rfind("}")
    if end != -1:
        try:
            return json.loads(t[:end + 1])
        except json.JSONDecodeError:
            pass
    # Terpotong: coba tutup string/kurung yang masih terbuka.
    try:
        return json.loads(_close_truncated(t))
    except json.JSONDecodeError as e:
        raise ValueError(f"Model tidak mengembalikan JSON:\n{text[:400]}") from e
