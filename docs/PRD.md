# PRD — PIKSTOCK Keyword Generator (Web v2)

**Status:** MVP v2 shipped (web UI). V1 = CLI + tkinter.
**Dibuat:** 2026-11-10
**Sumber:** `docs/PLAN.md`, `kwgen/`, `app_api/`, `web/`. Dokumen ini hanya menyatakan
perilaku yang ada di kode; nilai yang belum bisa dibuktikan ditandai
`UNVERIFIED — <alasan>`.

## 1. Problem

Penjual aset digital (clip art, ilustrasi, printable, mockup) perlu metadata
listing yang ditemukan pembeli. Model vision menjawab "gambar ini apa", bukan
"orang mencari apa". Tiap marketplace punya aturan tag yang berbeda, dan
memproses 40 gambar satu per satu tidak realistis.

## 2. Users

Satu pengguna lokal (owner workspace). Tool jalan di mesin sendiri, UI dibuka di
browser, tanpa multi-user, tanpa akun, tanpa cloud storage.

## 3. Goals

| # | Goal | Bukti di kode |
|---|---|---|
| G1 | Satu gambar → metadata SEO untuk 5 marketplace | `kwgen/formats.py` (`fmt_etsy`, `fmt_canva`, `fmt_creative_market`, `fmt_universal`, Adobe) |
| G2 | Aturan platform ditegakkan, bukan diasumsikan | `kwgen/constants.py` `KEYWORD_CAPS` + `cap_for()` |
| G3 | Ganti model AI tanpa ubah kode | `kwgen/router.py`, `config.json` (`router_url`, `api_key`, daftar model) |
| G4 | Batch puluhan gambar dengan progres live dan bisa batal | `POST /api/batch`, `GET /api/events/{batch_id}` (SSE), `POST /api/batch/{id}/cancel` |
| G5 | Pilih marketplace sebelum generate untuk menghemat panggilan AI | `picked_markets()` di `app_api/jobs.py`, `only=` pada `run_one()` |
| G6 | Riwayat run bisa dicari, dilihat, diekspor, dihapus | `GET /api/history`, `/api/history/{id}`, `DELETE /api/history[/{id}]`, `/api/history/keyword`, `/api/history/extract`, `/api/export.csv` |
| G7 | Aset web selalu segar saat dikembangkan | middleware `no-cache` untuk `/static/` di `app_api/context.py` |
| G8 | Deskripsi gambar saja tanpa keyword marketplace | `POST /api/extract`, `jobs.extract_one()`, `view-extract` |

## 4. Non-goals

- Bukan generator gambar. Tidak mengubah, me-retouch, atau mensintesis gambar.
- Tidak mengunggah ke marketplace. Hanya menghasilkan teks siap salin-tempel.
- Tidak ada sistem akun, login, atau sinkronisasi.
- Tidak ada inferensi milik tool sendiri; semua model lewat router eksternal
  (`CFG["router_url"]`).

## 5. Marketplace dan batas keyword

Plafon keras per platform (`kwgen/constants.py`), jumlah efektif =
`min(plafon, max_keywords())` dari config:

| Marketplace | Plafon |
|---|---|
| Etsy | 13 tag, maks 20 karakter/tag |
| Canva | 20 |
| Creative Market | 10 |
| Universal | 30 |
| Adobe Stock | 49 |

Etsy tag >20 karakter ditandai `OVER LIMIT` per baris dan dirangkum di blok
`PERINGATAN` (`kwgen/formats.py fmt_etsy`). Formatter tidak memotong tag; ia
melaporkan.

## 6. Alur utama

1. **Pilih sumber** — unggah satu berkas (`POST /api/generate`), pilih folder
   (`POST /api/select-folder` → dialog native `paths.py`), atau pilih berkas
   (`POST /api/select-file`).
2. **Pilih marketplace** (opsional). Tanpa pilihan, semua marketplace
   diproses.
3. **Generate.** Vision pass menghasilkan deskripsi 55–85 kata bahasa Inggris
   (`SYSTEM_PROMPT`), lalu pass per marketplace menghasilkan field spesifik.
4. **Lihat hasil** — kartu per marketplace, ringkasan sinyal, thumbnail grid.
5. **Batch** — `POST /api/batch` menjalankan worker thread; progres dikirim
   lewat SSE `GET /api/events/{batch_id}`; `POST /api/batch/{id}/cancel`
   menghentikan sisa antrean.
6. **Riwayat** — setiap run tersimpan di SQLite (`db.py`), bisa dibuka ulang,
   diekspor CSV, atau dihapus (satu atau semua). Riwayat dipisah per scope:
   keyword dan extract.
7. **Image Extract** — unggah satu atau banyak gambar ke `POST /api/extract` (satu request per gambar, berurutan, sama seperti Generate); satu vision
   call menghasilkan deskripsi visual plus atribut (jenis gambar, style, mood
   maks 2, tone, warna dominan maks 3, pencahayaan, komposisi, jenis produk).
   Field pilihan tetap (jenis gambar, pencahayaan, komposisi) dikosongkan
   bila tidak jelas; field lain bebas dari AI. Tanpa pass marketplace. Hasil disimpan sebagai run `source='extract'` dan tampil di
   Riwayat Extract.

## 7. Functional requirements

| ID | Requirement | Endpoint / modul |
|---|---|---|
| F1 | Terima unggahan gambar, batas 40 MB, tolak lebih dengan 413 | `POST /api/generate`, `MAX_UPLOAD_BYTES` |
| F2 | Berkas upload yang gagal diproses dihapus dari `uploads/` | `routes_jobs.py generate_upload` |
| F3 | Batch menerima `files[]` eksplisit atau memindai `folder` | `POST /api/batch` |
| F4 | Setiap `path` di batch harus berada di lingkup yang sah, selain itu 403 | `require_allowed()` |
| F5 | Thumbnail dibuat on-demand, di-cache di `generate/` dengan hash path+mtime | `GET /api/thumb`, `make_thumb()` |
| F6 | Thumbnail hanya untuk path sah dan ekstensi gambar | `require_allowed()` + `IMAGE_EXTS` |
| F7 | Folder/berkas dari dialog native atau `/api/scan` didaftarkan sebagai lingkup sah | `allow_folder()` |
| F8 | Config bisa dibaca dan diubah lewat API dengan validasi | `GET/PUT /api/config` |
| F9 | Riwayat menyimpan status, model terakhir, dan hasil per marketplace | `db.py`, `routes_history.py` |
| F10 | Ekspor CSV tersedia per run dan untuk semua run | `/api/history/{id}/export.csv`, `/api/export.csv` |
| F11 | Statistik agregat tersedia | `GET /api/stats` |
| F12 | Dialog file/folder dijalankan sebagai proses terpisah tanpa konsol | `native_dialog()`, `CREATE_NO_WINDOW` |
| F13 | Tombol **Lihat Trend** membuka card berisi input keyword yang otomatis terisi maksimal 5 dan pilihan negara; tombol **Buka Google Trends** membuka Google Trends yang sudah terisi keyword di tab baru, tanpa panggilan API | `web/js/trends.js`, `trends.google.com/trends/explore` |
| F15 | Baris riwayat gambar menampilkan jumlah gambar dan resolusi ("N gambar • WxH"); run lama tanpa data resolusi tampil "—" dan tidak di-backfill | `db.list_runs` (`sizes`, `images`), `web/js/history.js imageMetaHTML()` |
| F14 | Image Extract menerima banyak gambar ≤40 MB per file (staging, centang, progres per gambar, satu request per gambar), menyimpan deskripsi 55–85 kata plus atribut (asset_type, style, mood, tone, colors, lighting, composition, product_type) di `data`, dan memisahkan riwayat keyword/extract lewat parameter `scope`; hapus-semua memakai endpoint scope eksplisit | `POST /api/extract`, `DELETE /api/history/keyword`, `DELETE /api/history/extract`, `jobs.extract_one()`, `db.list_runs(scope=)`, `web/js/extract.js` |

## 8. Lingkup path (model keamanan)

Aplikasi ini membuka berkas dari disk atas permintaan HTTP. Lingkup yang sah:

- `uploads/` dan `generate/` — apa pun di dalamnya.
- Folder yang sudah dipilih user lewat dialog native, `/api/scan`, atau
  `folder` pada `/api/batch`. Didaftarkan sekali, berlaku selama proses hidup.

Selain itu → `403 path di luar lingkup tool`. Tidak ada akses ke drive liar,
berkas sistem, atau path traversal lewat `..` (path di-resolve sebelum
diperiksa). Registry bersifat in-memory: restart server mengosongkannya.

## 9. Non-functional requirements

| Area | Target | Status |
|---|---|---|
| Latensi halaman | LCP < 2.5 s lokal | UNVERIFIED — browser pass belum dijalankan |
| CLS | < 0.1 | UNVERIFIED — idem |
| A11y | 0 critical | UNVERIFIED — idem; kontrak di `docs/DESIGN.md` §11 |
| Keyboard | Semua aksi utama bisa dicapai keyboard | Ada di kode (chip `<button>`, history `role="button" tabindex="0"`, dropzone Enter/Space) |
| Reduced motion | Animasi mati saat `prefers-reduced-motion` | `web/responsive.css`, gate `!reduced` di `web/js/ui.js` |
| Offline | Tidak butuh internet selain router AI | Font & Motion dimuat dari CDN — lihat §12 |
| Data | Tanpa telemetri; API key router hanya di `config.json` lokal | Ada di kode |

## 10. Batasan teknis

- Python 3.13, FastAPI + uvicorn, tanpa build step frontend.
- Frontend: ES module plain JS (`web/js/`), CSS hand-written bertoken
  (`web/tokens.css`), Motion One.
- Penyimpanan: SQLite lokal + folder `uploads/`, `generate/`.
- Satu proses, satu pengguna. Tidak ada worker pool atau antrean persisten:
  batch yang sedang jalan hilang bila server restart (`JOBS` in-memory).

## 11. Risiko dan utang yang diketahui

| # | Risiko | Dampak | Status |
|---|---|---|---|
| R1 | `config.json` menyimpan `api_key` plaintext | Bocor bila folder dibagikan | Terbuka — tidak ada enkripsi |
| R2 | Registry folder sah hilang saat restart | Thumbnail/scan lama 403 sampai user memilih ulang | Diterima (by design) |
| R3 | Batch in-memory | Progres hilang saat restart; baris DB tertinggal | Terbuka |
| R4 | Font dan Motion dari CDN | Halaman tanpa internet kehilangan tipografi/motion | Terbuka |
| R5 | `docs/DESIGN.md` sempat rusak karena substitusi regex | Kepercayaan pada dokumen | Dipulihkan 2026-11-10, diverifikasi ulang |
| R6 | Progres bar masih menganimasikan `width` | Repaint per frame | Terbuka, tercatat di `DESIGN.md` §13 |

## 12. Acceptance criteria MVP v2

- [x] Satu gambar menghasilkan field untuk 5 marketplace sesuai plafon masing-masing.
- [x] Pilihan marketplace memangkas panggilan AI.
- [x] Batch berjalan dengan progres SSE dan tombol batal.
- [x] Riwayat tersimpan, bisa dibuka, diekspor CSV, dihapus.
- [x] Konfigurasi model dan API key diubah tanpa menyentuh kode.
- [x] `/api/thumb` menolak path di luar lingkup (403).
- [x] `/api/batch` memvalidasi setiap `path` sebelum worker dijalankan.
- [x] Unggahan >40 MB ditolak; berkas gagal tidak tertinggal di `uploads/`.
- [x] `ruff` bersih, `mypy` bersih, `pytest` lulus.
- [x] Tombol Lihat Trend mengisi maksimal 5 keyword dan negara, lalu membuka Google Trends di tab baru tanpa panggilan API.
- [x] Image Extract menyimpan deskripsi tanpa keyword, dan Riwayat keyword/extract terpisah.
- [ ] Browser pass untuk Image Extract (320/768/1280/1440) — belum dijalankan, user menolak browser pass.

## 13. Backlog (belum dikerjakan)

1. Enkripsi / keyring untuk `api_key`.
2. Persistensi batch agar progres tidak hilang saat restart.
3. Self-host font + Motion untuk pemakaian offline.
4. Ganti animasi `width` progres bar ke `transform: scaleX()`.
5. Browser pass untuk LCP/CLS/a11y (screenshot 320/768/1280/1440 + sloplint).
