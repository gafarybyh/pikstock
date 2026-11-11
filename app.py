"""app.py — SATU-SATUNYA pintu masuk Image Keyword Generator v2.

Cara pakai:
    python app.py

Yang terjadi:
  1. cari port yang masih bebas (mulai dari 7788)
  2. jalankan server lokal di 127.0.0.1
  3. buka browser otomatis
  4. Ctrl+C untuk berhenti

Opsi:
    python app.py --no-browser     jangan buka browser
    python app.py --port 9000      paksa port tertentu
"""
import argparse
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

BASE = Path(__file__).resolve().parent
HOST = "127.0.0.1"
DEFAULT_PORT = 7788


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((HOST, port))
            return True
        except OSError:
            return False


def pick_port(start: int) -> int:
    for p in range(start, start + 60):
        if port_free(p):
            return p
    raise SystemExit(f"Tidak ada port bebas di rentang {start}-{start + 59}.")


def wait_then_open(url: str, timeout: float = 30.0):
    """Tunggu server benar-benar siap, baru buka browser."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.4)
            if s.connect_ex((HOST, int(url.rsplit(":", 1)[1]))) == 0:
                try:
                    webbrowser.open(url)
                except Exception:
                    pass
                return
        time.sleep(0.25)


def main():
    ap = argparse.ArgumentParser(description="Image Keyword Generator v2")
    ap.add_argument("--port", type=int, default=None, help="port paksa (default: cari otomatis)")
    ap.add_argument("--no-browser", action="store_true", help="jangan buka browser")
    args = ap.parse_args()

    try:
        import uvicorn  # noqa: F401
    except ImportError:
        print("FastAPI/uvicorn belum terpasang.")
        print("Install:  pip install fastapi uvicorn python-multipart")
        sys.exit(1)

    sys.path.insert(0, str(BASE))
    try:
        import server  # noqa: F401  — memicu cek config & DB saat startup
    except Exception as e:
        print(f"Gagal memuat server: {e}")
        sys.exit(1)

    port = args.port or pick_port(DEFAULT_PORT)
    url = f"http://{HOST}:{port}"

    print("=" * 56, flush=True)
    print("  Image Keyword Generator", flush=True)
    print(f"  {url}", flush=True)
    print("  Tutup jendela ini atau Ctrl+C untuk berhenti.", flush=True)
    print("=" * 56, flush=True)

    if not args.no_browser:
        threading.Thread(target=wait_then_open, args=(url,), daemon=True).start()

    import uvicorn
    try:
        uvicorn.run("server:app", host=HOST, port=port, log_level="warning", access_log=False)
    except KeyboardInterrupt:
        pass
    print("\nServer berhenti.")


if __name__ == "__main__":
    main()
