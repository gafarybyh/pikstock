# Riset — Penyempurnaan System Prompt Keyword Generator

Dokumen riset untuk tuning prompt di `core.py`. Tujuan: setiap langkah AI
(`core`, `style`, `etsy`, `canva`, `creative_market`, `universal`, `adobe`)
menghasilkan metadata yang **sesuai cara kerja algoritma masing-masing
marketplace**, bukan satu prompt generik untuk semua.

**Tanggal riset:** 2026-10-18
**Status:** riset selesai + **sudah diimplementasikan** (lihat §13)
**Metode:** web research + verifikasi silang sumber resmi vs praktisi
+ uji generate nyata ke router `localhost:20128`.

---

## 0. Ringkasan eksekutif — 7 perubahan terpenting

| # | Temuan | Yang harus berubah di prompt |
|---|---|---|
| 1 | Etsy memakai **exact match** (frasa utuh) yang berbobot jauh lebih tinggi dari broad match | Tag Etsy harus **frasa 3-5 kata**, bukan kata tunggal |
| 2 | Etsy **tidak menumpuk** ranking bila keyword diulang di title & tag | Tag harus **melengkapi** title (long-tail), bukan menduplikasi |
| 3 | Etsy menormalisasi **plural & typo** secara otomatis | Dilarang membuang slot untuk `candle`/`candles` sekaligus |
| 4 | Adobe Stock: **10 keyword pertama** paling menentukan ranking | Output Adobe harus **terurut berdasarkan kepentingan** |
| 5 | Adobe Stock title ideal **< 70 karakter** (maks 200) | Batasi title Adobe, jangan 200 char penuh |
| 6 | Shutterstock/Freepik menilai **title lebih berat dari keyword** | Title `universal` harus kalimat deskriptif, bukan daftar kata |
| 7 | Semua platform memberi sanksi pada **keyword tidak relevan** (keyword dilution) | Wajib ada aturan anti-halusinasi + larangan filler |

---

## 1. Batas teknis per marketplace (hard constraints)

Ini **fakta terverifikasi** dan harus tercermin sebagai batas keras di kode,
bukan sekadar imbauan di prompt.

| Marketplace | Field | Batas | Catatan |
|---|---|---|---|
| **Etsy** | tag | 13 tag, **20 char/tag** (termasuk spasi) | Hanya huruf, angka, spasi |
| Etsy | title | 140 char | 40 char pertama paling penting |
| Etsy | description | 10.000 char | Paragraf pertama ikut dibaca algoritma |
| **Canva** | title | ~150 char (kolom judul) | Keyword-rich, dibaca manusia |
| Canva | tags | ±20 tag | Fokus niche & use-case |
| **Creative Market** | title | pendek, jelas, spesifik | Harus masuk akal di luar CM |
| Creative Market | tags | **5-10 tag relevan** | Bukan "tag terpopuler", tapi yang akurat |
| Creative Market | description | naratif | Bukan daftar kata |
| **Adobe Stock** | title | ideal **< 70**, maks **200** char | Batas 200 char dipertahankan di kode |
| Adobe Stock | keywords | 5-49 (**49 praktis**), min 15 untuk visibilitas | **Urutan = ranking** |
| **Freepik** | title | maks **100** char | Satu kalimat: who/what/when/where |
| Freepik | keywords | 5-50, **15-20 cukup** | AI generated wajib `_ai_generated` |
| **Shutterstock** | keywords | **7-50** | Better 25 akurat daripada 50 asal |
| Shutterstock | description | kalimat deskriptif | Bobot > keyword box |

> ⚠️ **Celah kode saat ini:** `KEYWORD_CAPS` di `core.py` memakai
> `adobe: 49` dan `universal: 30`. Batas itu hanya dipakai untuk **memotong**
> hasil, tapi tidak pernah diminta eksplisit ke model sebagai "max N".
> Model bisa membalas 60 lalu dipotong 49 → 11 keyword terbuang tanpa
> pernah dinilai berdasarkan mutu. Perbaikan: minta **tepat N** sejak awal.

---

## 2. Etsy — temuan paling berdampak

### 2.1 Dua jenis match, bobot berbeda

Etsy mencocokkan query pembeli dengan **tag** dan **title** melalui:

- **Exact match** — tag memuat frasa persis yang diketik pembeli → ranking
  jauh lebih tinggi.
- **Broad match** — tag memuat sebagian kata tapi tidak berurutan.

⇒ **Konsekuensi untuk prompt:** tag harus ditulis sebagai **frasa utuh yang
wajar diketik pembeli**, bukan potongan kata. `lavender soy candle` (19 char)
≫ `candle` + `lavender` + `soy`.

### 2.2 Tag ≠ title, keduanya menutup pencarian berbeda

Etsy memindai title **dan** tag. Mengulang keyword yang sama di keduanya
**tidak menambah ranking** (tidak ditumpuk). Title dibaca manusia sehingga
harus enak dibaca; tag tidak terlihat pembeli sehingga justru tempat
menampung frasa kaku, spesifik, dan long-tail.

⇒ **Konsekuensi untuk prompt:** instruksikan model menulis tag yang
**melengkapi** title — sinonim, konteks hadiah, konteks ruangan/pemakaian,
variasi bahan/gaya — bukan salinan kata title.

### 2.3 Normalisasi otomatis

Etsy menangani **plural** (`candle`/`candles`) dan **typo** pembeli secara
otomatis, serta memahami sinonim.

⇒ **Konsekuensi untuk prompt:** dilarang membuang slot untuk bentuk
tunggal/jamak dari kata yang sama. Ini kesalahan paling umum pada dataset
keyword yang dihasilkan AI.

### 2.4 Rumus membangun 13 tag (diadaptasi dari panduan praktisi)

Urutan yang terbukti, cocok dipetakan langsung ke instruksi prompt:

1. **Hero phrase** (2-4 kata) — deskripsi paling tepat produk → Tag 1
2. **3-5 variasi produk** — bahan, gaya, skala
3. **3 tag konteks hadiah** — penerima & momen (`gift for mom`,
   `housewarming gift`)
4. **2-3 tag use-case / estetika** — (`cozy kitchen decor`, `minimalist`)
5. **2 tag long-tail** — bahasa spesifik pembeli

### 2.5 Kesalahan yang menurunkan ranking (blacklist untuk prompt)

| Dilarang | Alasan |
|---|---|
| Slot tag kosong | Setiap slot kosong = peluang match yang hilang |
| Tag kata tunggal (`gift`, `art`) | Kompetisi jutaan listing |
| Typo yang disengaja | Etsy sudah auto-correct |
| Bahasa promosi (`sale`, `discount`, `best price`, `fast shipping`) | Tidak diketik pembeli saat mencari |
| Nama brand / nama toko | Pembeli tidak mencari nama toko dari search bar |
| Tag identik di semua listing | Bisa dianggap low-effort / ranking dikonsolidasi |
| Tag yang bertentangan dengan title (`Christmas` di title, `Easter` di tag) | Menurunkan relevansi |
| Kata umum berulang (`clip art` di 8 tag) | Boros slot, tidak menambah pertandingan |

---

## 3. Adobe Stock — urutan adalah ranking

Ini temuan yang **mengubah struktur output**, bukan cuma redaksi prompt.

### 3.1 Fakta dari sumber resmi Adobe

- Maksimum **49 keyword** per submission.
- **"Keyword order is essential and should reflect the content's importance."**
- **10 keyword pertama punya pengaruh terbesar** pada ranking.
- **"Use each keyword once"** — tidak boleh duplikat.
- Title: **"Keep it short, ideally under 70 characters."**
- Hindari istilah teknis/gear-heavy, nama artis, merek, orang nyata.

### 3.2 Pola keyword yang dianjurkan Adobe (contoh resmi)

| Pola | Contoh |
|---|---|
| Pisahkan elemen deskriptif | `White`, `fluffy`, `young animal`, `pup` |
| Campur umum + spesifik | `Animal`, `mammal`, `carnivore` |
| Lokasi | `London`, `England` |
| Konseptual | `Solitude`, `childhood`, `milestone`, `cold` |
| Jumlah orang | `One person`, `three people` |
| Setting | `Indoors`, `outdoors`, `day`, `night` |
| Sudut pandang | `High-angle view`, `aerial view` |
| Demografi model | `Black woman`, `Latinx teen`, `senior man` |

⇒ **Konsekuensi untuk prompt:** minta model mengeluarkan Adobe keywords
**sudah terurut penting → kurang penting**, dipecah per konsep (bukan frasa
panjang), dan mencakup kategori konseptual (mood, setting, viewpoint) —
bukan cuma nama objek.

### 3.3 Kesalahan yang membuat konten **ditolak** (bukan hanya turun ranking)

- Keyword tidak relevan → content refusal.
- Merek dagang, nama brand, info pribadi di metadata.
- Campur beberapa bahasa dalam satu submission.
- Keyword duplikat.

> Ini berarti instruksi "never invent objects" di prompt saat ini sudah
> benar arahnya, tapi **belum cukup keras** — perlu disebut eksplisit
> bahwa keyword spekulatif berisiko membuat aset ditolak, bukan cuma
> "kurang optimal".

---

## 4. Universal (Freepik / Shutterstock / stock image)

Kedua platform dipisah di kode (`universal` dipakai satu prompt), jadi
prompt harus memenuhi irisan aturan **yang paling ketat** dari keduanya.

### 4.1 Shutterstock

- **Title/description berbobot jauh lebih tinggi daripada keyword box.**
- Title harus **kalimat/frasa**, bukan daftar kata. Analogi resmi mereka:
  seperti *headline berita* — jawab Who, What, When, Where, Why, plus mood.
- Keyword: **7-50**; jangan isi semua slot kalau tidak relevan.
- **Jangan ulangi kata/kata majemuk yang sama.**
- **Keyword dilution**: mengisi 50 slot dengan kata asal-asalan justru
  menurunkan bobot subjek utama. Lebih baik 25 akurat daripada 50 biasa.
- Algoritma menghukum aset ber-CTR rendah → keyword tidak akurat merusak
  metrik jangka panjang.

### 4.2 Freepik (sekarang Magnific)

- Title maks **100 karakter**, satu kalimat jelas.
- Keyword: min 5, maks 50; **15-20 keyword relevan sudah cukup**.
- Deskripsikan **hanya yang terlihat**: subjek, setting, warna, gaya,
  mood, emosi. Sertakan sinonim & variasi.
- Larangan: pengulangan, daftar warna panjang, tag kampanye (`#summer`),
  filler generik (`cool`, `nice`, `fun`), **tipe file (`EPS10`, `JPG`)**,
  karakter khusus.
- Larangan judul: terlalu pendek/panjang, menyebut tipe file, angka/tanggal
  yang tidak kontekstual, karakter khusus.

### 4.3 Irisan aturan → jadi aturan prompt `universal`

- Title = satu kalimat deskriptif ≤100 char (memenuhi Freepik) dan
  bobotnya tinggi (memenuhi Shutterstock).
- Keywords: target **±30** (di antara 15-20 Freepik dan 25-50 Shutterstock),
  tanpa duplikat, tanpa tipe file, tanpa filler.
- Sertakan konsep/mood, bukan cuma objek.

---

## 5. Canva Creators

Canva tidak mempublikasikan panduan SEO kontributor yang setara Adobe.
Yang tersedia adalah dokumentasi program + praktik komunitas.

### 5.1 Fakta dari Canva

- Canva Creators: Template Creators, Element Creators, Specialty Creators.
- Royalti berbasis **frekuensi pemakaian** (usage/engagement), bukan
  penjualan per unit.
- Jangkauan ±85 juta pengguna di 190 negara; dianjurkan mendesain sesuai
  bahasa & budaya sendiri.
- Template yang mengisi **niche yang kurang terwakili** tampil lebih baik
  daripada desain generik karena kompetisi lebih rendah.

### 5.2 Praktik yang konsisten di sumber praktisi

- Judul deskriptif + kata kunci alami: `Editable Canva Planner Template for
  Small Business Owners` ≫ `Canva template bundle`.
- Sertakan kata pemicu yang dicari: `editable canva`, `digital download`,
  `business branding template`.
- Jelaskan format & jumlah item (`20 Canva Instagram post templates,
  fully editable`).
- Sebutkan elemen niche/segmen (`for real estate agents`, `for teachers`).

⇒ **Konsekuensi untuk prompt:** dorong model menyebut **niche/segmen
pemakai** dan **format + jumlah item** di title, karena itu pembeda utama
di marketplace yang padat.

> **Catatan kejujuran riset:** untuk Canva, bukti paling lemah di antara
> kelima marketplace. Tidak ada panduan resmi algoritma yang bisa dikutip.
> Instruksi Canva sebaiknya diperlakukan sebagai **hipotesis**, bukan fakta.

---

## 6. Creative Market

Sumber resmi (help center CM) memberi batasan yang jelas:

- **Product title**: pendek, jelas, spesifik. "Harus masuk akal bahkan di
  luar Creative Market" — diperlakukan sebagai *headline* produk.
- **Description**: harus langsung menjelaskan apa produknya, bagaimana
  dipakai, kenapa layak dibeli. Deskripsi bagus menaikkan visibilitas.
- **Tags: 5-10 tag relevan.** Tujuannya bukan tag terpopuler, tapi tag
  yang akurat dan membantu produk menonjol di kategorinya.
- Pencarian CM mencakup **title, tag, description, dan nama shop**.
- **Meta description** terpisah untuk Google — diperlakukan seperti mini-ads.
- Konten yang dibuat/di-generate AI **wajib** ditandai "Yes".

⇒ **Konsekuensi untuk prompt:** output `creative_market` sebaiknya
menghasilkan **title + deskripsi naratif + 5-10 tag**, bukan title +
deskripsi saja seperti sekarang. Ini sekaligus menghapus ketergantungan
langkah `style` hanya untuk melengkapi use-case.

---

## 7. Prinsip lintas-platform (berlaku untuk SEMUA langkah)

Temuan yang berulang di kelima marketplace, jadi layak dijadikan aturan
global di `SEO_RULES()`:

1. **Akurasi mengalahkan kuantitas.** Semua platform menghukum keyword
   tidak relevan. Jangan pernah mengarang objek yang tidak terlihat.
2. **Pikirkan seperti pembeli, bukan ilustrator.** Pakai bahasa yang
   benar-benar diketik orang saat mencari, bukan istilah teknis
   (`sine wave border` → `wavy border`).
3. **Frasa mengalahkan kata tunggal.** Berlaku di Etsy (exact match),
   Adobe (konsep spesifik), Shutterstock (title berbobot).
4. **Jangan ulang.** Etsy tidak menumpuk ranking; Adobe & Shutterstock
   melarang duplikat. Duplikasi hanya memboroskan slot.
5. **Front-load.** 40 char pertama title Etsy, 10 keyword pertama Adobe,
   kata pertama title Shutterstock — semuanya berbobot lebih.
6. **Larangan keras:** merek dagang, nama orang/artis nyata, nama karakter
   fiktif, info pribadi (jalur penolakan aset di Adobe).
7. **Larangan filler:** `cool`, `nice`, `beautiful`, `sale`, `discount`,
   tipe file, karakter khusus.
8. **Satu bahasa** per output (Inggris) — campur bahasa = penolakan.

---

## 8. Diagnosa system prompt saat ini

Prompt yang ada di `core.py`:

### 8.1 `SYSTEM_PROMPT` (vision, baris 79-82)

```text
You describe digital clip art images for a marketplace SEO analyst.
Reply with ONE short plain-text paragraph (max 60 words) describing ONLY what is visible:
subject, elements, colours, art style, medium, and plausible buyer use cases.
No JSON, no markdown, no preamble, no questions.
```

**Kekuatan:** batas 60 kata, "ONLY what is visible" (anti-halusinasi), larangan
markdown. Ini sudah sesuai tujuan pipeline dua tahap (deskripsi kecil →
7 JSON kecil).

**Kelemahan:**

| # | Masalah | Dampak |
|---|---|---|
| 1 | Tidak meminta **subjek utama dulu, lalu detail** | Step 2 kehilangan sinyal apa kata kunci utama |
| 2 | Tidak meminta **teks/tulisan di dalam gambar** (jika ada) | Clip art bertulisan kehilangan keyword penting |
| 3 | "plausible buyer use cases" undang halusinasi, karena tahap 1 seharusnya **hanya** deskriptif | Info palsu terbawa ke semua langkah |
| 4 | Tidak ada larangan menyebut **merek / karakter IP** (mis. menebak "Disney style") | Risiko penolakan aset di Adobe |
| 5 | Tidak meminta **bentuk/latar transparan**, padahal krusial untuk clip art | Keyword `transparent background` sering dicari pembeli |
| 6 | Instruksi bahasa tidak gamlang kalau model menjawab non-Inggris | Sebagian model gratis membalas bahasa lain |

### 8.2 `SEO_SPECS()` (baris 111-133) + `SEO_RULES()` (baris 136-139)

```text
Rules: all text in ENGLISH. Favour phrasing buyers actually type, not technical jargon.
Only describe what the visual description supports; never invent objects.
Reply with the JSON object only - no markdown fence, no commentary.
```

**Kekuatan:** Inggris, bahasa pembeli, anti-halusinasi, JSON-only.

**Kelemahan (yang paling mahal):**

| # | Masalah | Dampak |
|---|---|---|
| 1 | Tag Etsy hanya dibatasi "MAX 20 CHARACTERS", tanpa aturan **frasa** | Model menghasilkan tag kata tunggal → kalah exact match |
| 2 | Tidak ada larangan **plural/duplikat** | `flower` + `flowers` memboroskan slot |
| 3 | Tidak ada instruksi **tag melengkapi title** | Tag menduplikasi title |
| 4 | Adobe tidak diminta **terurut penting** | 10 keyword pertama bisa berisi keyword lemah |
| 5 | Adobe title diminta "max 200 chars" | Sumber resmi: ideal < 70 char |
| 6 | `creative_market` tidak meminta **tag** | Kehilangan 5-10 slot gratis yang direkomendasikan CM |
| 7 | `universal` minta "%d English stock-image tags" tapi title tidak diminta | Title berbobot > keyword di Shutterstock, jadi ini kehilangan besar |
| 8 | Tidak ada larangan **merek/artis/orang nyata** | Risiko penolakan aset |
| 9 | Tidak ada larangan **filler & jenis file** | Keyword `EPS10`, `nice` lolos |
| 10 | "Favour phrasing buyers actually type" terlalu abstrak | Tidak bisa dieksekusi model kecil/gratis |
| 11 | Tidak ada permintaan **konsep/mood/setting** untuk stock | Hasil hanya objek literal |

---

## 9. Rencana tuning prompt (usulan — belum diterapkan)

Diurutkan berdasarkan **dampak × risiko**. Semua perubahan teks prompt saja,
tidak mengubah kontrak `build_keywords()`.

### Fase A — perubahan kecil, dampak besar (risiko rendah)

| # | Target | Perubahan |
|---|---|---|
| A1 | `SYSTEM_PROMPT` | Urutkan wajib: subjek utama → elemen → warna → gaya → medium → bentuk/latar. Hapus "buyer use cases" (pindah ke langkah `style`, tempatnya lebih tepat). Tambah: baca teks yang terlihat, sebut latar transparan/putih bila ada. Larang menebak merek/karakter. |
| A2 | `SEO_RULES()` | Tambah blacklist eksplisit: tanpa tipe file, tanpa karakter khusus, tanpa filler (`cool/nice/beautiful/sale/discount`), tanpa merek/artis/orang nyata, tanpa duplikat. |
| A3 | `etsy` spec | Tambah: setiap tag **frasa 3-5 kata**; tanpa duplikat kata; tanpa bentuk tunggal/jamak dari kata yang sama; lengkapi title, jangan menduplikasi; 13 slot terisi semua. |
| A4 | `adobe` spec | Tambah: **urutkan keyword paling penting dulu, 10 pertama paling menentukan**; satu konsep per keyword; sertakan konsep/mood/setting; title ideal < 70 char. |

### Fase B — perubahan struktur output (risiko sedang, perlu cek UI/CSV)

| # | Target | Perubahan | Dampak ke kode lain |
|---|---|---|---|
| B1 | `universal` spec | Minta **title** juga (`{"title","tags"}`) | `build_keywords`, `fmt_universal`, `csv_rows` perlu field baru |
| B2 | `creative_market` spec | Minta **tags 5-10** juga | `fmt_creative_market`, `csv_rows` perlu field baru |
| B3 | `canva` spec | Tegaskan niche/segmen + format + jumlah item di title | Tidak ada (format sama) |

> Fase B menyentuh `data` dict, formatter, dan CSV. Harus dikerjakan
> **satu per satu** dengan test, jangan sekaligus.

### Fase C — pasca-tuning (opsional)

- Ganti `KEYWORD_CAPS` menjadi sumber tunggal yang juga **disuntikkan ke
  prompt** (sekarang batas di prompt dan batas di kode bisa tidak sinkron).
- Tambah validasi pasca-generate ringan di Python (bukan prompt):
  deteksi duplikat/plural, tag >20 char Etsy, keyword `< 15` Adobe →
  laporkan di `_errors` atau `_warnings`.

---

## 10. Risiko & catatan kejujuran

- **Model gratis sulit mematuhi prompt panjang.** `docs/PLAN.md` mencatat model
  `:zero_cost_coding` menolak JSON besar. Menambah aturan berpotensi
  memperkecil kepatuhan. **Mitigasi:** aturan per-langkah singkat & imperatif
  (bukan esai), dan verifikasi dengan generate nyata, bukan hanya asumsi.
- **Tidak ada data volume pencarian.** Semua sumber ini adalah aturan
  *kualitas & relevansi*, bukan data kuantitatif. Tool ini tetap tidak bisa
  memberi estimasi volume — jangan menjanjikan itu.
- **Batas platform bisa berubah.** Angka di dokumen ini adalah kondisi saat
  riset (Oktober 2026). Direkomendasikan dicek ulang tiap ±6 bulan.
- **Kekuatan bukti tidak seragam:**

| Marketplace | Kekuatan bukti | Sumber utama |
|---|---|---|
| Adobe Stock | **Kuat** — dokumentasi resmi Adobe Stock | helpx.adobe.com |
| Shutterstock | **Kuat** — help center resmi contributor | submit.shutterstock.com |
| Etsy | **Sedang** — batas resmi (13/20) + mekanik dari praktisi | help.etsy.com (batas), listingview.io (mekanik) |
| Creative Market | **Sedang** — help center resmi | support.creativemarket.com |
| Freepik | **Sedang** — panduan komunitas/CSV, bukan halaman kebijakan resmi | photokeyworder.ai, rastock.ai |
| Canva | **Lemah** — tidak ada panduan algoritma resmi | canva.com/help (umum) + praktisi |

---

## 11. Sumber

**Resmi / semi-resmi**

- Adobe Stock — *Tips for effective titles and keywords*
  https://helpx.adobe.com/stock/contributor/content-policies-guidelines/metadata/tips-effective-titles-keywords.html
- Shutterstock — *Description and Keyword Best Practices*
  https://submit.shutterstock.com/help/en/articles/10594702-description-and-keyword-best-practices
- Etsy — *How to Use Tags to Get Found in Search* (batas 13 tag / 20 char)
  https://help.etsy.com/hc/en-us/articles/360000336307
- Creative Market — *Creating High-Quality Product Description Pages (PDPs)*
  https://support.creativemarket.com/hc/en-us/articles/43335464121499
- Creative Market — *Best Practices for Searching on Creative Market*
  https://support.creativemarket.com/hc/en-us/articles/201367770
- Canva — *About the Canva Creators program*
  https://www.canva.com/help/canva-creators-program

**Praktisi / sekunder**

- ListingView — *Etsy Tags Best Practices in 2026: The Full Playbook*
  https://listingview.io/blogs/etsy-tags-best-practices-in-2026-the-full-playbook
- TypeCount — *Etsy Character Limits 2026*
  https://typecount.com/blog/etsy-character-limit
- Printify — *Mastering Etsy tags*
  https://printify.com/blog/etsy-tags
- CyberStock — *Adobe Stock Title & Keyword Guidelines 2026*
  https://cyberstock.lol/blog/adobe-stock-title-keyword-guidelines-2026
- PhotoKeyworder — *Adobe Stock Contributor Guide (CSV metadata)*
  https://blog.photokeyworder.ai/2026/05/29/the-complete-adobe-stock-contributor-guide
  dan *Magnific (ex-Freepik) Contributor Guide*
  https://blog.photokeyworder.ai/2026/06/29/the-complete-magnific-ex-freepik-contributor-guide
- Meita — *Shutterstock Search Algorithm: Boost Keyword Ranking*
  https://meita.ai/blog/shutterstocks-search-algorithm-optimizing-keywords-for-maximum-visibility
- Rastock — *Freepik Keywording Rules That Actually Get Enforced*
  https://rastock.ai/blog/freepik-keywording-rules
- Insight Agent — *Best Etsy Tags for Digital Art (2026 Guide)*
  https://www.insightagent.app/guides/best-etsy-tags-for-digital-art
- Printful — *How to make money on Canva in 2026*
  https://www.printful.com/blog/how-to-make-money-on-canva

---

## 12. Langkah berikutnya

Riset ini **belum mengubah kode apa pun**. Rekomendasi urutan eksekusi:

1. Setujui Fase A (A1-A4) — hanya teks prompt, tanpa perubahan kontrak data.
2. Terapkan A1-A4 di `core.py`.
3. Verifikasi dengan generate nyata: 1 gambar, ke-5 marketplace dicentang,
   periksa hasil nyata (bukan asumsi) untuk tiap kriteria:
   - Tag Etsy semuanya frasa & ≤20 char, tanpa duplikat
   - Adobe keywords terurut & 10 pertama relevan
   - Tidak ada filler/tipe file/merek
4. Setelah Fase A terbukti stabil, pertimbangkan Fase B satu per satu.

---

## 13. Yang sudah diimplementasikan (2026-10-18)

Fase A **dan** Fase B dikerjakan sekaligus, plus perbaikan yang tidak
terduga saat uji nyata. Semua perubahan ada di `core.py`, `web/app.js`.

### 13.1 Prompt

| Target | Perubahan |
|---|---|
| `SYSTEM_PROMPT` | Ditulis ulang: bukan lagi "clip art" tapi **produk digital** (clip art, ilustrasi, foto, printable, pola, template, mockup). Urutan wajib subjek → elemen → warna → gaya/medium → latar/komposisi → teks yang terlihat → mood. Panjang 45-70 kata. Larangan menebak merek/franchise/artis/orang nyata. |
| `SEO_RULES` | Dari fungsi jadi **konstanta**. Ditambah: dedupe & larangan pasangan tunggal/jamak, larangan tipe file, filler, kata promosi, karakter khusus, merek/artis/orang nyata. |
| `STEP_RULES` (baru) | Aturan khusus yang hanya disuntik ke langkah terkait: `etsy` (tag = frasa 2-5 kata, tag pertama = nama produk) dan `adobe` (urutan penting→kurang, 1 konsep/keyword, sertakan setting/mood/konsep). |
| `SEO_SPECS` | Etsy: "lowercase, phrase 2-5 words, max 20 chars". Canva: wajib sebut segmen pembeli + format file. Creative Market: minta **10 tag**. Universal: minta **title** deskriptif 60-100 char. Adobe: title "at most 200, ideally under 70". |
| `seo_step` | Perintah disusun sebagai daftar bagian lalu digabung — memperbaiki bug **titik ganda** (`words..`) dan fragmen kalimat berhuruf kecil. |

### 13.2 Kode (bukan prompt)

| Target | Perubahan |
|---|---|
| `KEYWORD_CAPS` | Tambah `creative_market: 10`. |
| `_clean_tags` (baru) | Dedupe berbasis kata dasar terurut (jadi `flower`/`flowers` dianggap sama), buang filler/tipe file/tag tanpa huruf, buang `None`, potong di batas kata. |
| `quality_warnings` (baru) | Laporan lunak `_warnings` bila tag di bawah batas minimal platform atau `universal_title` kosong. Tidak membatalkan hasil. |
| `build_keywords` | Field baru `creative_market_tags`, `universal_title`. Semua tag dilewatkan `_clean_tags`. |
| `fmt_creative_market`, `fmt_universal` | Menampilkan tag & title baru. |
| `csv_rows` | Ikut mengekspor tag Creative Market & title Universal. |
| `web/app.js` | Kartu Creative Market & Universal menampilkan field baru; `payloadFor` (Copy) dan cek sinyal ikut menyertakannya. |

### 13.3 Temuan saat uji nyata (tidak terlihat dari riset)

1. **Tag Etsy tanpa kata produk.** Uji generate nyata menghasilkan 13 tag
   yang semuanya konteks hadiah/pemakaian (`botanical wall decor`,
   `mothers day present`, …) — tidak satu pun menyebut produknya
   (`flower illustration`). Diperbaiki dengan aturan
   "tag pertama harus hero phrase nama produk".
2. **`None` jadi tag `"none"`** dan angka `123` jadi tag `"123"` di
   `_clean_tags`. Diperbaiki: buang `None`, dan buang tag tanpa huruf.
3. **Titik ganda** pada prompt (`...words..`) dan fragmen kalimat berhuruf
   kecil karena penggabungan string manual.

### 13.4 Verifikasi yang benar-benar dijalankan

| Cek | Hasil |
|---|---|
| `import core` / `import server` | PASS |
| `node --check web/app.js` | PASS |
| Prompt tiap langkah: tanpa titik ganda, tiap kalimat kapital | PASS (7 langkah) |
| `_clean_tags`: 10 kasus tepi (plural, filler, `None`, angka, cap, tanda baca) | PASS |
| `build_keywords` end-to-end dengan `_post` dipalsukan | PASS |
| Subset `only=["etsy"]` → langkah lain tidak dipanggil | PASS (1 panggilan) |
| **Generate nyata** ke `localhost:20128`, 5 marketplace | PASS, 19-30 s, `errors: None`, `warnings: None` |

### 13.5 Yang belum dikerjakan

- ~~**Fase C** (§9)~~ **SELESAI — lihat §14.** `cap_for()` kini jadi sumber
  tunggal; Adobe mengikuti `max_keywords` (30), bukan memaksa 49.
- Uji UI di browser sungguhan (verifikasi hanya pada level kode/JS syntax).
- Tuning ulang bila ganti model: perilaku prompt bergantung model.

---

## 14. Fase C — perbaikan cacat + bukti nyata (2026-10-18, lanjutan)

Fase B sudah lulus semua tes, **tapi audit terhadap hasil sungguhan**
(§13.5) menemukan cacat yang tidak tertangkap tes. Bagian ini mencatat
perbaikannya dan bukti A/B pada **gambar yang sama**.

### 14.1 Cacat yang ditemukan dari audit hasil nyata

| # | Cacat | Bukti | Sifat |
|---|---|---|---|
| 1 | `BANNED` hanya mencocokkan **seluruh tag**, bukan kata di dalamnya | tag `spring sale graphic` (hasil nyata) lolos; `svg file`, `eps10 vector` juga lolos | Bug kode — guardrail hampir kosmetik |
| 2 | Judul Canva membocorkan kata literal **"buyer"** | `Potted flower bouquet art for home decor buyers, digital download` | **Regresi dari prompt Fase B** (spesifikasi menyuruh "name the buyer segment") |
| 3 | 3 `alt_titles` berakhir sama | semua diakhiri `, digital download` | Regresi ringan |
| 4 | `fit_tag` membuang kata yang sah | tag tepat 20 karakter → kata terakhir hilang (`a very long tag name` → `a very long tag`) | Bug lama, bukan dari Fase B |
| 5 | Contoh frasa di prompt **disalin mentah** oleh model | setelah contoh `'cat lovers' / 'nursery decor'` dipasang, **4 dari 5** judul Canva memakai "nursery decor" | Ditemukan saat uji A/B Fase C |

Cacat 5 penting sebagai pelajaran: **contoh konkret di prompt akan
disalin**, jadi prompt harus meminta kata dari gambar itu sendiri,
bukan memberi contoh yang bisa di-copy.

### 14.2 Perubahan kode

| Target | Perubahan |
|---|---|
| `BANNED_TAGS` / `BANNED_WORDS` | Dipisah. `BANNED_TAGS` = tag yang isinya persis kata terlarang. `BANNED_WORDS` = kata yang membuang **seluruh** tag walau hanya muncul sebagai salah satu kata (tipe file + promosi). `BANNED` tetap ada sebagai alias agar kode lama tidak pecah. |
| `_clean_tags` | Cek `BANNED_WORDS.intersection(words)` setelah normalisasi. |
| `_clean_title` (baru) | Buang `buyer/buyers/customer/customers/audience`, rapikan sambung yang menggantung (`art for buyers` → `art`), kapital di awal. |
| `_clean_titles` (baru) | Versi daftar untuk `alt_titles`; buang yang kosong/duplikat. |
| `cap_for(market)` (baru) | **Satu sumber kebenaran**: `min(KEYWORD_CAPS[market], max_keywords())`. Dipakai prompt **dan** pemotongan hasil. |
| `build_keywords` | Semua `cap=` memakai `cap_for(...)`, bukan angka mati. Semua judul lewat `_clean_title`. |
| `fit_tag` | Hanya mundur ke spasi bila potongan benar-benar di tengah kata. |
| `SEO_SPECS["canva"]` | Larang kata "buyer/customer/audience"; minta kata dari tema gambar itu sendiri (**tanpa** memberi contoh yang bisa disalin); 3 alt title wajib beda struktur & akhir. |
| `web/index.html` | Hint pengaturan ditulis ulang: satu nilai `max_keywords` berlaku untuk semua marketplace. |

### 14.3 Penyatuan plafon dengan konfigurasi

Sesuai keputusan: **Adobe tidak lagi memaksa 49.** Semua marketplace
memakai satu pengaturan yang sama.

| Marketplace | Plafon platform | Efektif (`max_keywords=30`) |
|---|---|---|
| Etsy | 13 | 13 |
| Creative Market | 10 | 10 |
| Canva | 20 | 20 |
| Universal | 30 | 30 |
| Adobe Stock | 49 | **30** (ikut config) |

Kalau `max_keywords` dinaikkan ke 49, Adobe otomatis jadi 49 tanpa
mengubah kode — karena `cap_for()` membaca config saat dipanggil.

### 14.4 Bukti A/B — gambar yang sama, prompt lama vs baru

5 gambar, hasil lama tersimpan di `tmp/*.json` dibandingkan hasil baru
pada berkas gambar yang identik. Total 154 detik, `errors: None` di
semua gambar.

| Metrik (Etsy) | Sebelum | Sesudah | |
|---|---|---|---|
| Tag memuat tipe file / kata promosi | 2 | **0** | membaik |
| Pasangan tunggal–jamak | 5 | **1** | membaik |
| Tag-1 menyebut jenis produk | 0/5 | **5/5** | membaik |
| Tag > 20 karakter | 0 | 0 | tetap |
| Duplikat tag | 0 | 0 | tetap |
| Jumlah tag | 13/13 | 13/13 | tetap |

| Metrik judul | Sebelum | Sesudah |
|---|---|---|
| Judul memuat "buyer/customer" | 2 hasil nyata (pra-Fase C) | **0** |
| Judul Adobe ≤ 70 karakter | 0/5 (field belum ada) | **5/5** |
| `alt_titles` berakhir berbeda | 15/15 | 15/15 |
| Judul Canva memakai contoh yang disalin | 4/5 (percobaan pertama) | **0/4** |

**Yang tidak bisa dibandingkan (jujur):** `adobe_tags` dan
`universal_title` **belum ada** di hasil lama, jadi angka `0 → 30` dan
`0 → 5` di atas adalah **kemampuan baru**, bukan peningkatan prompt.
Metrik Etsy dan judul Canva-lah yang benar-benar sebanding.

### 14.5 Sisa masalah yang diketahui

1. **Pasangan tunggal–jamak lintas frasa** masih bisa lolos: `rolling
   green hills` + `sunrise hill scene` menghasilkan `hills`/`hill` di
   dua tag berbeda. Dedupe saat ini hanya menormalkan **satu tag utuh**,
   belum memeriksa akar kata yang sama di tag lain. Perlu keputusan
   produk: membuangnya bisa menghilangkan frasa yang sah.
2. **Tag Etsy satu kata** masih muncul sesekali (`housewarming`). Secara
   aturan lemah, tapi bukan pelanggaran platform.
3. **`adobe_single_pct` tinggi (93-100%)** — model menuruti aturan "one
   concept per keyword" dengan sangat harfiah. Perlu dinilai apakah ini
   terlalu ekstrem untuk ranking Adobe (belum ada bukti).
4. **Sampel kecil**: 5 gambar, satu model (`kl/gpt-6-luna`). Perilaku
   bisa berbeda pada model lain.
5. Uji UI di browser sungguhan masih belum dilakukan (verifikasi hanya
   level kode + `node --check`).

### 14.6 Verifikasi

| Cek | Hasil |
|---|---|
| `check_core`, `check_prompt`, `check_e2e`, `check_edge` | **PASS** (4/4) |
| `check_faseC` (baru): 11 kasus buang + 9 kasus simpan, 7 kasus judul, 13 kasus cap, 4 anti-regresi | **PASS** (44/44) |
| `import core` / `import server` | **PASS** |
| `node --check web/app.js` | **PASS** |
| Prompt 7 langkah: tanpa titik ganda | **PASS** |
| A/B 5 gambar nyata | **PASS**, 0 error |
