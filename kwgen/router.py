"""kwgen.router - POST ke router AI dengan fallback model berurutan."""

import json
import urllib.error
import urllib.request

from .config import CFG, MODELS

LAST_MODEL = ""

RETRYABLE = {400, 401, 404, 410, 429, 500, 502, 503}  # model mati / no credential / overloaded


def api_key():
    return str(CFG.get("api_key", "")).strip()


def _loads(raw):
    """Router kadang mengirim beberapa objek JSON berurutan; ambil yang pertama."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        obj, _ = json.JSONDecoder().raw_decode(raw.lstrip())
        return obj


def _post(payload, model=None):
    """Kirim satu request. Model dicoba berurutan dari MODELS sampai ada yang hidup.

    Content kosong / JSON rusak dianggap gagal -> lanjut ke model berikutnya.
    """
    global LAST_MODEL
    last = "no model configured"
    for m in ([model] if model else MODELS):
        body = dict(payload, model=m)
        req = urllib.request.Request(
            CFG["router_url"], data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {api_key()}"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=int(CFG.get("timeout_seconds", 120))) as r:
                data = _loads(r.read().decode())
            text = data["choices"][0]["message"].get("content") or ""
            if not str(text).strip():  # model hidup tapi balas kosong
                last = f"{m} -> balasan kosong"
                continue
            LAST_MODEL = m
            return text
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:400]
            last = f"{m} -> HTTP {e.code}: {msg}"
            if e.code not in RETRYABLE:
                raise RuntimeError(last) from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Tidak bisa konek ke router ({CFG['router_url']}): {e.reason}") from e
        except (KeyError, IndexError, TypeError):
            last = f"{m} -> respons tidak berisi choices"
        except json.JSONDecodeError as e:
            last = f"{m} -> JSON rusak: {e}"
    raise RuntimeError("Semua model gagal. Terakhir: " + last)
