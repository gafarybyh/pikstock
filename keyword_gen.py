"""keyword_gen.py — GUI tkinter lama (v1). Masih berfungsi sebagai fallback.

Semua logika ada di core.py. Untuk versi web (v2) jalankan:  python app.py
"""
import json
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import core

BASE = Path(__file__).resolve().parent
HAVE_PIL = core.HAVE_PIL

if HAVE_PIL:
    from PIL import Image, ImageTk


class App:
    def __init__(self, root):
        self.root = root
        root.title("Image Keyword Generator")
        root.geometry("1000x680")
        self.path = None
        self.photo = None
        self.result = None

        bar = ttk.Frame(root, padding=8)
        bar.pack(fill="x")
        ttk.Button(bar, text="Pilih Gambar", command=self.choose).pack(side="left")
        self.name = ttk.Label(bar, text="(belum ada gambar)")
        self.name.pack(side="left", padx=10)
        self.gen = ttk.Button(bar, text="Generate Keyword", command=self.generate, state="disabled")
        self.gen.pack(side="right")
        self.save_btn = ttk.Button(bar, text="Simpan", command=self.save, state="disabled")
        self.save_btn.pack(side="right", padx=6)

        body = ttk.Panedwindow(root, orient="horizontal")
        body.pack(fill="both", expand=True, padx=8, pady=8)

        left = ttk.Frame(body)
        self.preview = ttk.Label(left, text="Preview", anchor="center", relief="groove")
        self.preview.pack(fill="both", expand=True)
        body.add(left, weight=1)

        right = ttk.Frame(body)
        self.nb = ttk.Notebook(right)
        self.tabs = {}
        for key in ("Etsy", "Canva", "Creative Market", "Universal", "JSON"):
            f = ttk.Frame(self.nb)
            txt = tk.Text(f, wrap="word", font=("Consolas", 10))
            txt.pack(fill="both", expand=True)
            txt.configure(state="disabled")
            self.nb.add(f, text=key)
            self.tabs[key] = txt
        self.nb.pack(fill="both", expand=True)
        ttk.Button(right, text="Copy tab ini", command=self.copy).pack(pady=4)
        body.add(right, weight=2)

        self.status = ttk.Label(root, text="Siap.", anchor="w")
        self.status.pack(fill="x", padx=8, pady=(0, 8))

    def choose(self):
        p = filedialog.askopenfilename(
            filetypes=[("Gambar", "*.png *.jpg *.jpeg *.webp *.gif *.bmp"), ("Semua", "*.*")])
        if not p:
            return
        self.path = p
        self.name.config(text=Path(p).name)
        self.gen.config(state="normal")
        self.save_btn.config(state="disabled")
        self.preview_img(p)

    def preview_img(self, p):
        try:
            if HAVE_PIL:
                im = Image.open(p)
                im.thumbnail((420, 560))
                self.photo = ImageTk.PhotoImage(im)
            elif Path(p).suffix.lower() in (".png", ".gif"):
                self.photo = tk.PhotoImage(file=p)
            else:
                raise ValueError("butuh PIL untuk format ini")
            self.preview.config(image=self.photo, text="")
        except Exception as e:
            self.preview.config(image="", text=f"Preview tidak tersedia\n({e})")
            self.photo = None

    def generate(self):
        self.gen.config(state="disabled")
        self.status.config(text="Memproses via 9router...")
        threading.Thread(target=self._work, daemon=True).start()

    def _work(self):
        try:
            data = core.build_keywords(self.path)
            self.root.after(0, self._done, data, None)
        except Exception as e:
            self.root.after(0, self._done, None, e)

    def _done(self, data, err):
        self.gen.config(state="normal")
        if err:
            self.status.config(text=f"GAGAL: {err}")
            messagebox.showerror("Error", str(err))
            return
        self.result = data
        self.set("Etsy", core.fmt_etsy(data))
        self.set("Canva", core.fmt_canva(data))
        self.set("Creative Market", core.fmt_creative_market(data))
        self.set("Universal", core.fmt_universal(data))
        self.set("JSON", json.dumps(data, indent=2, ensure_ascii=False))
        self.save_btn.config(state="normal")
        self.status.config(text="Selesai. Cek peringatan Etsy, lalu Copy.")

    def set(self, tab, text):
        w = self.tabs[tab]
        w.configure(state="normal")
        w.delete("1.0", "end")
        w.insert("1.0", text)
        w.configure(state="disabled")

    def copy(self):
        cur = self.nb.tab(self.nb.select(), "text")
        text = self.tabs[cur].get("1.0", "end").strip()
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status.config(text=f"'{cur}' disalin ke clipboard.")

    def save(self):
        out = core.save_outputs(self.path, self.result)
        self.status.config(text=f"Tersimpan: {out}")


if __name__ == "__main__":
    r = tk.Tk()
    App(r)
    r.mainloop()
