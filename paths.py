"""paths.py — dialog pilih folder/file native (tkinter), dijalankan sebagai subprocess.

Kenapa subprocess: dialog tkinter hanya bisa dibuka dari thread utama proses GUI.
Server FastAPI jalan di thread/event-loop lain, jadi dialog harus di proses terpisah.
Server memanggil:  subprocess.run([sys.executable, "paths.py", "--folder"])
Keluar dengan kode 0 = dipilih, 1 = dibatalkan.

Juga dipakai baris perintah:  python paths.py --folder
"""
import sys
import tkinter as tk
from tkinter import filedialog

IMAGE_PATTERN = "*.png *.jpg *.jpeg *.webp"


def ask_folder(parent_title="Pilih folder gambar"):
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        p = filedialog.askdirectory(title=parent_title)
    finally:
        root.destroy()
    return p


def ask_file():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        p = filedialog.askopenfilename(
            title="Pilih gambar",
            filetypes=[("Gambar", IMAGE_PATTERN), ("Semua", "*.*")])
    finally:
        root.destroy()
    return p


def ask_files():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        paths = filedialog.askopenfilenames(
            title="Pilih gambar (bisa banyak)",
            filetypes=[("Gambar", IMAGE_PATTERN), ("Semua", "*.*")])
    finally:
        root.destroy()
    return list(paths)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "--folder"
    try:
        if mode == "--file":
            result = [ask_file()]
        elif mode == "--files":
            result = ask_files()
        else:
            result = [ask_folder()]
    except Exception as e:  # tidak ada display / tkinter gagal
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
    result = [p for p in result if p]
    if not result:
        sys.exit(1)
    print("\n".join(result))
