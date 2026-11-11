# Image Keyword Generator — PLAN

**Status:** MVP v1 selesai (CLI/GUI tkinter) → **MVP v2 dibangun: versi Web**
**Dibuat:** 2026-10-17
**Owner:** Raynor (workspace agent)

## Tujuan

Tool personal untuk mengubah **gambar clip art / ilustrasi** menjadi **keyword SEO siap-listing** untuk dijual di marketplace (Canva Contributor, Etsy, Creative Market, Universal, dan Adobe Stock).

Bukan tool regenerasi gambar. Fokusnya: **biar listing ditemukan pembeli.**

## Masalah yang diselesaikan

| Masalah | Solusi |
|---|---|
| Model vision hanya menjawab "gambar ini apa", bukan "orang cari apa" | Lapis prompt SEO: gaya pasar, intent pembeli, variasi long-tail |
| Tiap marketplace punya aturan berbeda (Etsy: 13 tag × 20 karakter) | Formatter + validator per marketplace |
| Ganti model AI = ubah kode | Semua lewat 9router, OpenAI-compatible → ganti model cukup edit `config.json` |
| Tkinter mentok untuk preview, batch, dan riwayat | MVP v2: UI web (browser), pipeline Python tetap sama |
| 40 gambar = 40× klik | Mode batch dengan progres live dan bisa batal |
| Generate selalu memproses **semua** marketplace (sampai 8 panggilan AI/gambar) walau cuma butuh satu | **Pilih marketplace sebelum generate**: hanya langkah AI yang dibutuhkan pasar terpilih yang dijalankan. 1 pasar = 2 panggilan (vision + 1) |

## Arsitektur MVP v2

```
                    Browser (HTML/CSS/JS + Motion)
                    ┌──────────────────────────┐
                    │  1 gambar │ folder │ batch │
                    │  kartu hasil per marketplace │
                    └──────────┬───────────────┘
                          SSE progres live
                    ┌──────────▼───────────────┐
                    │  server.py  (FastAPI)    │
                    │  + paths.py dialog folder│
                    └───┬──────────────────┬───┘
                        │                  │
              ┌─────────▼──────┐   ┌───────▼────────┐
              │   core.py      │   │    db.py       │
              │  vision → SEO  │   │ SQLite riwayat │
              │  (murni, tanpa │   │ runs/projects  │
              │   UI, sama spt │   └───────┬────────┘
              │   keyword_gen) │           │
              └─────────┬──────┘     ┌─────▼──────┐
                        │            │ generate/    │
              ┌─────────▼──────┐     │ *.webp     │
              │ 9router :20128 │     └────────────┘
              └────────────────┘

Entry point tunggal:  python app.py
  → cari port bebas → jalankan uvicorn → buka browser otomatis
```

### Prinsip arsitektur

- **`core.py` bebas UI.** Semua logika keyword tinggal di sini. GUI tkinter (v1) dan web (v2) sama-sama memakainya. Menambah UI ketiga tidak menyentuh logika.
- **Pipeline dua tahap tetap.** Batas ukuran JSON per panggilan — see "Temuan teknis penting".
- **Riwayat dulu, tren belakangan.** Skema DB dirancang agar mudah diperluas (lihat "Fondasi untuk Fase 3").

## Keputusan

- **2026-10-17** — Pakai 9router `http://localhost:20128/v1`, bukan API langsung per provider. Terbukti mendukung input gambar base64. `config.json` hanya boleh berisi base URL — script menambah `/chat/completions` sendiri.
- **2026-10-17** — API key dibaca **hanya** dari `config.json` (`api_key`). Dukungan env var (`api_key_env`) dihapus total demi kesederhanaan.
- **2026-10-17** — Tanpa fitur tren di MVP. Tidak ada API publik gratis untuk volume pencarian Canva/Etsy; auto-suggest scrape ditunda.
- **2026-10-17 (v2)** — **UI pindah ke web lokal**, bukan desktop. Alasannya: preview gambar, batch grid, dan riwayat jauh lebih cepat dibangun di browser daripada tkinter.
- **2026-10-17 (v2)** — **Tanpa login, tanpa multiuser.** Satu user di satu mesin. Tidak ada tabel user, tidak ada session, tidak ada auth. URL hanya bind ke `127.0.0.1`.
- **2026-10-17 (v2)** — **Motion (motion.dev) versi vanilla JS, di-cache lokal** di `web/vendor/motion.min.js`. Bukan CDN supaya aplikasi tetap jalan offline. Kalau file cache hilang, halaman jatuh ke CDN sebagai cadangan.
- **2026-10-17 (v2)** — **Frontend HTML/CSS/JS murni, tanpa build step dan tanpa `node_modules`.** Tidak ada React/Vite/npm. Alur kerja: edit file lalu refresh browser.
- **2026-10-17 (v2)** — **Stack backend: FastAPI + uvicorn** (sudah terpasang di mesin). Dipakai untuk SSE (server-sent events) agar progres batch bisa dikirim live ke browser tanpa polling berat.
- **2026-10-17 (v2)** — **Riwayat pakai SQLite bawaan Python (`sqlite3`).** Nol dependency tambahan. Skema: `projects`, `batches`, `runs`.
- **2026-10-17 (v2)** — **Jendela dialog native untuk pilih folder.** Browser tidak bisa membaca path asli dari disk (sandbox), jadi `paths.py` membuka dialog tkinter di proses terpisah (`subprocess`), lalu hasilnya dikirim balik ke server. Rasanya tetap web, tapi folder tetap bisa dipilih.
- **2026-10-17 (v2)** — **`app.py` sebagai satu-satunya entry point.** Pengguna cukup `python app.py` (atau klik dua kali). App itu sendiri cari port bebas → jalankan server → buka browser. Tidak ada langkah manual.
- **2026-10-17 (v2)** — **Pengaturan bisa diedit dari web** (menu Pengaturan): base URL router, model utama, fallback model, API key, sisi maksimal gambar, timeout, folder sementara. Sumber data tetap `config.json`; server menulis secara atomik (merge, key tak dikenal dipertahankan) lalu `core.reload_config()` me-rebind `CFG`/`MODELS`, jadi **berlaku tanpa restart**. API key **tidak pernah** dikirim balik ke browser — hanya `has_key` + 4 karakter terakhir.
- **2026-10-17 (v2)** — **Lapisan sinyal keyword = Google Suggest** (`signals.py`), bukan API marketplace. Alasan: gratis, tanpa key, berlaku lintas-market. Autocomplete Etsy sudah mati (404/403 — lihat "Temuan teknis"), dan Canva/Creative Market/Adobe tidak punya API keyword gratis — jangan tampilkan angka kompetisi karangan untuk mereka. Kompetisi hanya bisa diukur di Etsy (Open API v3 `count`, butuh key gratis, label khusus Etsy) — opsional, belum diambil. Arah tren musiman nanti lewat `trendspy` (`pytrends` archived Apr 2025) — opsional, belum diambil.

- **2026-10-17 (v2)** — **Adobe Stock jadi kartu marketplace ke-5**, bukan lagi menumpang tag "Universal". Punya Title sendiri (≤200 char) + keyword sendiri (plafon 49, efektif dibatasi setting `max_keywords` ≤30 agar JSON tetap kecil). Prompt `universal` tak lagi menyebut Adobe Stock.
- **2026-10-17 (v2)** — **Pilih marketplace sebelum generate.** Checkbox inline di view Single & Batch (awal kosong, wajib centang ≥1, ingat pilihan di `localStorage kw.marketplaces`). `build_keywords(path, on_step, only)` hanya menjalankan langkah AI yang dibutuhkan pasar terpilih; hasil menyimpan `_marketplaces` sehingga kartu pasar yang tak dipilih disembunyikan (riwayat lama tanpa `_marketplaces` → tampil semua). Dipilih ketimbang pilihan tersimpan di `config.json` supaya cepat diakses per-tugas.
- **2026-10-17 (v2)** — **Tab "Satu gambar" menjadi "Unggah gambar" (banyak gambar).** Bisa unggah beberapa file sekaligus (drag-drop atau file picker `multiple`) **dan** pilih beberapa file dari disk (`/api/select-files` → `paths.py --files` pakai `askopenfilenames`). Antrean ditampilkan sebagai grid thumbnail dengan hapus per-item. Diproses **berurutan** lewat `runAll()` (tanpa perubahan backend: tiap gambar memanggil `/api/generate` atau `/api/generate-path` yang sudah ada, jadi tetap 1 baris riwayat + `tmp/*.json` per gambar). Hasil ditumpuk kartu penuh. Alasan berurutan ketimbang paralel: aman untuk router AI + progres `i/N` jelas.

## Langkah

### Fase 1 — v1 (SELESAI)

- [x] Riset existing solutions (CLIP-Interrogator, img2prompt, WD14, JoyCaption, Qwen3-VL, Gemini)
- [x] Probe 9router — endpoint & vision OK
- [x] docs/PLAN.md
- [x] `config.json` — endpoint, model, path
- [x] `keyword_gen.py` — GUI + vision call + formatter + validator
- [x] Uji dengan gambar clip art sintetis (`test_clipart.png`) — 3/3 run sukses, ~15 detik

### Fase 2 — v2 Web (SELESAI, sisa uji manual)

- [x] Refactor: `keyword_gen.py` → `core.py` (logika bebas UI) + `db.py` (SQLite riwayat)
- [x] `paths.py` — dialog pilih folder native via subprocess
- [x] `server.py` — FastAPI: static, scan folder, generate single, batch + SSE, history CRUD
- [x] `web/index.html` + `app.css` + `app.js` — 3 mode, kartu hasil, Motion, responsif
- [x] `web/vendor/motion.min.js` — cache lokal Motion
- [x] `app.py` — launcher tunggal: auto pilih port, jalankan uvicorn, buka browser
- [x] Uji API: single generate, batch 2 gambar via SSE, riwayat (list/detail/cari/thumb), hapus satu run
- [x] Uji UI di browser sungguhan: Motion termuat, layout kartu, tombol copy, drawer riwayat, hapus, batch 1 gambar + tombol batal tampil
- [x] Uji dialog folder native (subprocess tkinter) — smoke test, bukan dari klik UI
- [x] Menu **Pengaturan** di web: `GET/PUT /api/config`, form model/base URL/fallback/API key/proses, simpan tanpa restart, key tidak pernah ditampilkan penuh
- [x] Pengaturan **jumlah keyword per marketplace** (`max_keywords`, 5-30, default 30): satu nilai berlaku untuk **semua** marketplace. `cap_for(market)` = `min(KEYWORD_CAPS[market], max_keywords())` dipakai baik saat menyusun prompt maupun memotong hasil (Etsy 13, Creative Market 10, Canva 20, Universal 30, Adobe Stock 49 — diambil yang terkecil, jadi dengan config 30 Adobe efektif 30)
- [x] Kartu **Adobe Stock** (Title ≤200 char + keyword sendiri) — kartu ke-5
- [x] **Pilih marketplace sebelum generate**: checkbox inline Single+Batch, `only` diteruskan ke `build_keywords`, kartu tak terpilih disembunyikan, wajib ≥1, ingat di localStorage
- [x] **Unggah gambar banyak**: tab "Unggah gambar" terima beberapa file (upload & disk), grid thumbnail + hapus, proses berurutan, hasil kartu penuh tertumpuk
- [x] **Tab Riwayat diperkaya**: grup tanggal (Hari ini/Kemarin/tanggal) + header sticky, filter status (Semua/Berhasil/Gagal) & sumber (Unggah/Disk/Batch), hitungan "Menampilkan X dari Y", mode pilih → hapus massal + pilih semua, **undo hapus 5 detik** (DELETE ditunda, tanpa ubah skema DB), navigasi drawer ←/→ + tombol "Buka gambar" + label sumber. Backend: `db.list_runs(...,status,source)` + fix `total` ikut filter (dulu selalu `COUNT(*)`), `db.delete_runs(ids)`, `DELETE /api/history?ids=`.
- [x] **Riwayat gambar: jumlah + resolusi.** Baris kedua di item riwayat scope `image` menampilkan "N gambar • WxH". Backend: `db.list_runs` ikut mengambil `sizes` dan `images`, `_run_row` mem-parse keduanya. Frontend: `imageMetaHTML(h)` di `web/js/history.js`. Catatan: run yang dibuat sebelum perubahan ini tidak punya `sizes`, sehingga tampil "1 gambar • —". Tidak di-backfill.
- [ ] Uji batch lebih besar (4+ gambar) dan tombol batal
- [ ] Uji dengan clip art asli hasil karya sendiri (butuh user)

### Fase 3 — Tren & Skor (SEBAGIAN SELESAI)

- [x] Sinyal demand lintas-market via Google Suggest (`signals.py`) — kuat/sedang/lemah, cache 7 hari di tabel `signals`, tanpa key, degradasi anggun tanpa internet
- [x] UI: tombol **Cek sinyal** di kartu hasil → badge warna per tag (kuat hijau, sedang ungu, lemah redup, `n/a` putus-putus)
- [x] Ekspor CSV: per run (`/api/history/{id}/export.csv`) + semua run (`/api/export.csv`), 6 kolom flat `run_id, filename, created_at, marketplace, type, value`, BOM Excel
- [x] Uji: `python -m pytest -q test/test_signals.py` (classify + csv_rows) + smoke API live (signals hidup dari Google, cache lintas-restart, CSV terparse 6 kolom)
- [x] Perbaikan Cek sinyal: **semua** tag dicek (dulu terpotong 60 di frontend + 80 di backend → kini batas tunggal `max_signal_terms` di menu Pengaturan, default 150 ≥ 103 maks). Chip duplikat antar-kartu semuanya diwarnai (dulu hanya chip terakhir, sisanya memantul selamanya). `.is-checking` selalu dibersihkan (jalur sukses maupun gagal). Query head dibuat malas → hemat ~1 panggilan per tag panjang. UI memberi tahu bila terpotong.
- [ ] Arah tren musiman via `trendspy` — opsional, belum diambil
- [ ] Kompetisi Etsy (Open API v3 `count`) — opsional, butuh key gratis, label khusus Etsy
- [ ] Kolom skor di DB + UI tabel banding keyword — ditunda sampai ada kolom tren/kompetisi

## Temuan teknis penting

**Model gratis `:zero_cost_coding` menolak membalas JSON besar.** Gejala:
- Diminta skema 13-field → balas prosa / SVG / JSON mini (`{"keywords":[...]}`).
- Konsisten diulang: bukan masalah `max_tokens` atau "coba lagi".

**Solusi yang dipakai — pipeline dua tahap:**
1. Tahap 1: gambar → deskripsi teks pendek (≤60 kata), `max_tokens=400`.
2. Tahap 2: deskripsi → **sampai 7 panggilan JSON kecil terpisah** (`core`, `style`, `etsy`, `canva`, `creative_market`, `universal`, `adobe`), masing-masing `max_tokens=1600`. Hanya langkah yang dibutuhkan marketplace terpilih yang dijalankan (`only`); tanpa pilihan = semua (7).
   Satu bagian gagal tidak membatalkan hasil lain; error dicatat di `_errors`.
   Kalau model tetap kehabisan token di tengah JSON, `parse_json()` membuang string setengah jadi lalu menutup kurung yang terbuka (`_close_truncated`) — bukan gagal total.

Pelajaran: saat memakai routing ke model gratis, **batasi ukuran output JSON per panggilan** (~<1 KB), jangan minta satu objek besar.

**Autocomplete Etsy mati; Google Suggest hidup (probe 2026-10-17).** Endpoint lama Etsy (`/suggestions/v2/search`, `/search/suggestions`) balas 404/403, dan halaman pencarian Etsy balas 403 (bot detection) dari mesin lokal — scrape Etsy tidak bisa diandalkan. `suggestqueries.google.com/complete/search?client=firefox&q=…` balas 200 tanpa key. Cache sinyal 7 hari di tabel `signals`; kegagalan jaringan → status `n/a`, bukan error.

## Diagnosis 2026-10-17 — generate gagal setelah pindah router

Empat bug ditemukan & diperbaiki:

| # | Masalah | Perbaikan |
|---|---|---|
| 1 | `router_url` diisi base `.../v1` saja | Script menyambung `/chat/completions` otomatis; menerima base maupun endpoint penuh |
| 2 | Combo `open_code_free` → `muse-spark-1.3-contributor-free` sudah **deprecated** (HTTP 410) | `fallback_models` di config; `_post()` mencoba model berurutan pada 400/401/404/410/429/5xx |
| 3 | `ANTHROPIC_API_KEY` di env berisi key Cherry Studio (`cs-sk-...`) dan **menimpa** key router → 401 | Sumber key dipersempit: **hanya `api_key` di `config.json`**. Dukungan env var dihapus sepenuhnya |
| 4 | Tag Etsy dipotong buta `[:20]` → `"potted flower clipar"` | `fit_tag()` memotong di batas kata (`"potted flower"`) |

Model vision yang **terbukti hidup** di `localhost:20128`:
`zero_cost_coding`, `oc/mimo-v2.6-flash-free`, `oc/space-bunny-free`.
Mati: `paid_model` (CLIENT_MODEL_NOT_AVAILABLE), semua prefix `th/` (tidak ada credential), `oc/longcat-2.5-preview-free` (balasan kosong).

## Struktur file

```
projects/image-keyword-generator/
  PLAN.md                 ← dokumen ini
  app.py                  ← ⭐ ENTRY POINT: python app.py (cari port → uvicorn → buka browser)
  server.py               ← tipis: import core/db/signals + app_api (24 route terdaftar)
  app_api/                ← paket FastAPI, satu modul per kelompok route
    __init__.py           ← urutan import = urutan registrasi route
    context.py            ← BASE/WEB/GENERATE/UPLOADS, objek app, middleware revalidate static
    jobs.py               ← JOBS in-memory, scan folder, run_one, batch_worker, SSE stream
    routes_pick.py        ← /api/select-folder, /api/select-files, /api/thumb, /api/scan
    routes_jobs.py        ← /api/generate, /api/batch, /api/batch/{id}/cancel, /api/events/{id}
    routes_history.py     ← /api/history*, /api/stats, ekspor CSV
    routes_signals.py     ← /api/signals, /api/signals/stream
    routes_config.py      ← GET/PUT /api/config (key tak pernah dikirim balik)
    routes_static.py      ← mount /generate, /static, index, 404 → SPA fallback
  core.py                 ← wajah publik: re-export semua isi paket kwgen/ (pemanggil lama tetap jalan)
  kwgen/                  ← logika keyword (bebas UI), dipecah 11 modul
    __init__.py           ← re-export seluruh API core
    config.py             ← config.json read/save/reload (atomik), CFG, MODELS, max_keywords, max_signal_terms
    constants.py          ← SYSTEM_PROMPT, SEO_RULES, STEP_RULES, KEYWORD_CAPS, MARKET_STEPS, SEO_SPECS
    imaging.py            ← encode_image (downscale bila PIL ada) + HAVE_PIL
    router.py             ← _post ke 9router + fallback model + LAST_MODEL
    parsing.py            ← parse_json + _close_truncated
    text.py               ← fit_tag, _clean_tags/_clean_title(s), quality_warnings
    urls.py               ← strip_urls (dipakai signals)
    pipeline.py           ← call_vision, seo_step, build_keywords
    formats.py            ← fmt_etsy/canva/creative_market/universal/adobe + fmt_all
    csvio.py              ← CSV_HEADER, csv_rows
    outputs.py            ← save_outputs (tmp/*.json + tmp/*.txt)
  paths.py                ← dialog pilih folder / file (satu atau banyak) native (subprocess, sekali jalan)
  db.py                   ← skema SQLite + CRUD riwayat + cache sinyal
  signals.py              ← sinyal demand via Google Suggest (kuat/sedang/lemah)
  test_signals.py         ← self-check tanpa jaringan (python test_signals.py)
  keyword_gen.py          ← CLI/fallback (lama,tkinter) — tetap bisa dipakai
  config.json             ← router_url, model, api_key, fallback_models (JANGAN di-commit)
  web/
    index.html            ← shell: 5 <link> CSS + <script type="module" src="/static/js/main.js">
    app.css               ← @import shell (fonts → tokens → layout → components → responsive)
    tokens.css            ← custom properties
    layout.css
    components.css
    responsive.css
    fonts.css
    js/                   ← ES module, tanpa build step
      main.js             ← bootstrap: loadStats, wireChrome, hook binding, showView('single')
      core.js             ← $, M (Motion), state, esc, fmt*, MARKETS, localStorage key
      ui.js               ← toast, copy, popover, skeleton, showView, chip
      render.js           ← kartu hasil + mount (container._data)
      upload.js           ← antrean unggah banyak gambar
      batch.js            ← mode batch folder + progres SSE + batal
      history.js          ← riwayat, filter, multi-select, undo hapus
      settings.js         ← form /api/config
      markets.js          ← checkbox marketplace → localStorage
      signals.js          ← cek sinyal Google Suggest
    vendor/motion.min.js  ← Motion cache lokal
  data/history.db         ← SQLite riwayat
  generate/                 ← cache thumbnail webp
  tmp/                    ← output JSON/TXT per gambar (dari save_outputs)
  shots/                  ← bukti screenshot QA (tidak dipakai runtime)
```

## Cara pakai

**Web (utama):**
```
cd projects/image-keyword-generator
python app.py
```
Atau klik dua kali `app.py`. App cari port bebas → buka server → buka browser otomatis.

Lalu: **centang marketplace** yang diinginkan (Etsy/Canva/Creative Market/Universal/Adobe Stock — minimal satu) │ **Unggah gambar** (bisa banyak sekaligus, dari upload atau disk) │ **Batch folder** │ riwayat di panel kiri │ **Pengaturan** (model, base URL, key, parameter proses).

**CLI/fallback:**
```
python keyword_gen.py   # GUI tkinter lama (masih berfungsi)
```

Ganti model / base URL / API key: buka menu **Pengaturan** di web, lalu **Simpan**. Perubahan langsung dipakai tanpa restart. Kalau model utama mati/deprecated (410), script otomatis pindah ke model di daftar fallback. (Alternatif lama: edit `config.json` manual lalu restart.)

## Batasan yang diketahui

- **Browser tidak bisa pilih path absolut.** Ini alasan kenapa ada `paths.py`. Dialog folder/file (satu atau banyak) dibuka di proses terpisah.
- **Batch boros waktu & kuota.** Sampai 8 panggilan AI per gambar (1 vision + 7 langkah market) bila semua marketplace dipilih; turun sesuai centang (1 pasar = 2 panggilan). 40 gambar ≈ 10 menit saat semua aktif. Ada tombol batal. Jangan proses gambar terlalu banyak sekaligus.
- **Unggah banyak file berurutan, bukan paralel.** Tab "Unggah gambar" memproses antrean satu per satu; file upload disimpan di memori sebagai blob sampai diproses/dihapus, jadi hindari ratusan file besar sekaligus (pakai Batch folder untuk volume besar).
- **Ekspor TXT (`fmt_all`) tetap mencetak semua header marketplace** walau hanya sebagian yang dipilih (bagian yang tak dipilih kosong). CSV sudah otomatis bersih karena baris kosong dibuang.
- Kualitas keyword bergantung pada model yang dipetakan 9router. Model tidak tahu volume pencarian real-time — ia memberi **kosakata yang relevan + konvensional**, bukan data SEO kuantitatif.
- Validator Etsy hanya menegakkan batas karakter/jumlah — bukan kualitas relevansi.
- `data/history.db` dan `config.json` (berisi API key plaintext) **tidak boleh** di-commit ke repo publik.

## Fondasi untuk Fase 3 (tren)

Skema `runs` di `db.py` sudah punya kolom yang bisa dipakai ulang tanpa migrasi besar: `data` (JSON blob) bisa menampung skor tren per keyword nanti. Sumber sinyal sudah diputuskan: **Google Suggest** (`signals.py`, tersimpan di tabel `signals`, TTL 7 hari) sebagai basis lintas-market. Yang masih opsional dan belum diambil: `trendspy` (arah tren musiman) dan Etsy Open API v3 `count` (kompetisi khusus Etsy).