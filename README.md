# Image Keyword Generator

Tool untuk mengubah gambar clip art / ilustrasi menjadi keyword SEO siap-listing untuk marketplace: Canva Contributor, Etsy, Creative Market, Universal, dan Adobe Stock.

Bukan generator gambar. Fokusnya: membantu listing ditemukan pembeli.

## Fitur

- Satu gambar atau banyak gambar sekaligus (unggah atau pilih dari disk).
- Batch folder dengan progres live (SSE) dan tombol batal.
- Pilih marketplace sebelum generate: hanya langkah AI yang dibutuhkan yang dijalankan.
- Riwayat tersimpan (SQLite): cari, filter, ekspor CSV, hapus dengan undo 5 detik.
- Riwayat gambar menampilkan jumlah gambar dan resolusi.
- Cek sinyal demand via Google Suggest.
- Image Extract: deskripsi visual + atribut tanpa keyword marketplace.
- Pengaturan model, base URL, API key, dan jumlah keyword langsung dari UI.

## Kebutuhan

- Python 3.13
- Router AI kompatibel OpenAI (contoh: 9router) di `config.json`

## Instalasi

```
pip install -r requirements.txt
```

Untuk pengembangan (lint, test):

```
pip install -r requirements-dev.txt
```

## Konfigurasi

Buat atau edit `config.json` di root proyek:

```json
{
  "router_url": "http://localhost:20128/v1",
  "model": "nama-model",
  "api_key": "isi-api-key",
  "fallback_models": []
}
```

`config.json` berisi API key plaintext. Jangan di-commit.

## Menjalankan

```
python app.py
```

App mencari port bebas, menjalankan server, dan membuka browser otomatis.

CLI lama (GUI tkinter) masih tersedia:

```
python keyword_gen.py
```

## Struktur

```
app.py              entry point
server.py           FastAPI, mount route dari app_api/
app_api/            route per kelompok (jobs, history, signals, config, pick, static)
core.py             logika keyword, bebas UI
db.py               SQLite riwayat
signals.py          sinyal Google Suggest (cache 7 hari)
paths.py            dialog pilih folder/file native
web/                frontend ES module tanpa build step
test/               pytest
docs/               PRD, PLAN, DESIGN
```

## Batasan

- Browser tidak bisa memilih path absolut. Dialog folder/file dibuka di proses terpisah.
- Batch memanggil AI per gambar: sampai 8 panggilan bila semua marketplace dipilih.
- Kualitas keyword bergantung pada model. Model tidak punya data volume pencarian real-time.
- Validator Etsy hanya memeriksa batas karakter dan jumlah, bukan relevansi.

## Pengujian

```
python -m pytest -q test/
```

## Dokumentasi

Lihat `docs/PRD.md`, `docs/PLAN.md`, dan `docs/DESIGN.md`.
