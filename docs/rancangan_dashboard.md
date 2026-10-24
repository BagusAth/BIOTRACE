# Rancangan dashboard satu halaman BioTrace (belum diimplementasikan)

Acuan visual: mockup "Dashboard verifikasi eDNA · satu halaman" (`Main.dc.html`). Acuan isi:
PRD v2 dan mesin BioTrace tahap 0–7 di repo ini. Dokumen ini hanya rancangan.

## 1. Prinsip

1. **Mesin Python tetap satu-satunya sumber kebenaran.** Dashboard tidak menghitung ulang nilai,
   keputusan, atau penyebab; ia hanya menampilkan keluaran `biotrace.pipeline.run()`.
2. **Satu kontrak data** (`biotrace.report.v1`, JSON) dipakai oleh dashboard, mode statis, dan uji.
   Angka di layar, CSV, dan PDF berasal dari objek yang sama (PRD tahap 5: "isinya sama").
3. **Tidak ada angka yang ditulis tangan.** Angka di mockup hanya contoh; beberapa bertentangan
   dengan hasil mesin (lihat bagian 9).
4. **Jejak audit terlihat:** versi referensi, versi aturan, SHA-256 berkas, dan sidik jari laporan
   selalu tampil.

## 2. Pemetaan mockup → PRD → sumber data

| Blok di mockup | PRD | Sumber di mesin sekarang | Yang perlu ditambah |
|---|---|---|---|
| Header: proyek, referensi, aturan, Unggah/Ekspor | F1, F4, F24 | `manifest["referensi"]`, `rules.version`, `report.write_outputs` | nama proyek (input pengguna) |
| Banner SIMULASI | NFR kejujuran demo | `Report.simulation`, `is_simulation()` | — |
| Judul + chip (marker, stasiun × replikat, N klaim dari M ASV, tanggal) | F1 | `project.metadata`, `audit.site_info()`, `claims` | agregasi chip; waktu proses (tidak di-hash) |
| Ringkasan keputusan + 4 kartu penyaring | F22 | `report.decision_summary()` | — |
| Penyebab ketidakpastian (batang) | F17 | kolom `penyebab` | hitung klaim per penyebab |
| Data masuk dan jejak audit | F3, F4 | `project.files`, `project.issues` | deskripsi berkas (format, jumlah baris) |
| Tabel klaim + pil penyaring | F22 | `report.claims` (skema PRD) | — |
| Evidence Card + tombol ID/EN | F18, F19, F21, F23 | `report.evidence_card()`, `galat_nilai`, `asal_usul` | alasan terstruktur (skor/maks per lapisan); asal-usul sebagai 3 butir |
| Peta celah kamus | F7, F25 | `kelengkapan.csv`, `kelengkapan_spesies.csv`, `report.gap_map()` | agregasi per kelompok (Telmatherinidae endemik, endemik lain, introduksi) |
| Daftar prioritas barcode + unduh CSV | F25 | `report.barcode_priority()` | — |
| Footer: versi + sidik jari | F4 | `manifest`, `report.fingerprint` | — |

## 3. Arsitektur yang diusulkan

```
 Browser
   │  Next.js (App Router, React, TypeScript, Tailwind)
   │  /                    unggah data atau muat demo
   │  /laporan/[runId]     dashboard satu halaman
   ▼
 Next.js server ── rewrite /api/* ──►  FastAPI  (biotrace/api.py, lapisan tipis)
                                          │
                                          ▼
                                   paket biotrace (tidak berubah aturannya)
                                   io → naming (BLAST+) → audit → scoring → decision
                                          │
                                          ▼
                                   biotrace/dto.py  → ReportDTO "biotrace.report.v1"
                                          │
                                          ▼
                                   run store: out/runs/<sidik-jari>/
                                     report.json · klaim.csv · laporan.pdf
                                     prioritas_barcode.csv · manifest.json

 Mode statis (pitch): python -m biotrace run ... --json → web/public/demo/report.json
                      → next build (output: export) → hosting statis tanpa server Python
```

Alasan pilihan:

- **Mesin tetap Python** karena bergantung pada BLAST+, pandas, dan referensi berversi; memindahkannya
  ke JavaScript berisiko mengubah hasil dan melanggar reproduksibilitas.
- **FastAPI** cukup tipis: menerima unggahan, memanggil `pipeline.run()`, menyimpan hasil, dan
  menyajikan JSON serta berkas ekspor. Skema Pydantic sekaligus menghasilkan JSON Schema.
- **Next.js** memberi kontrol penuh atas tata letak mockup (sulit ditiru rapi di Streamlit), plus
  ekspor statis untuk demo pitch.
- **ID run = sidik jari laporan** (16 karakter heksa pertama). Input dan versi yang sama →
  ID yang sama → hasil di-cache dan bisa dibagikan sebagai URL. Ini mewujudkan US7 di antarmuka.
- Streamlit (`app.py`) tetap dipertahankan sebagai cadangan selama transisi.

## 4. Kontrak data `biotrace.report.v1`

Garis besar (nama kolom mengikuti istilah PRD):

```json
{
  "schema": "biotrace.report.v1",
  "meta": {
    "proyek": "Pemantauan Danau Matano",
    "judul": "Danau Matano, MTN-ST1 sampai MTN-ST3",
    "simulasi": true,
    "marker": ["12S MiFish-U"],
    "jumlah_stasiun": 3, "replikat_per_stasiun": 3,
    "jumlah_klaim": 15, "jumlah_asv": 10,
    "diproses": "2026-10-24T21:05:00+08:00",
    "durasi_detik": 1.2,
    "referensi": {"label": "ref12S v0.1 (sha256:…)", "versi": "v0.1", "jenis": "indonesia", "wilayah": "Kompleks Malili"},
    "aturan": {"versi": "0.1", "sha256": "…"},
    "aplikasi": "biotrace 0.2.0",
    "sidik_jari": "sha256:…"
  },
  "ringkasan": {"kalimat": "Dari 15 klaim, …", "jumlah": {"aman dilaporkan": 8, "…": 0}, "tindak_lanjut": {"…": "…"}},
  "penyebab": [{"kode": "referensi", "label": "Referensi", "petunjuk": "kerabat belum ada di kamus", "jumlah": 6}],
  "berkas": [{"nama": "bacaan.csv", "peran": "bacaan", "deskripsi": "tabel bacaan, format panjang, 43 baris", "sha256": "…"}],
  "informasi_hilang": [{"berkas": "aturan", "masalah": "tag_jump_fraction belum dikalibrasi", "dampak": "…", "tingkat": "info"}],
  "klaim": [{
    "id": "asv07@MTN-ST2", "asv": "asv07", "stasiun": "MTN-ST2", "danau": "Matano",
    "nama_lab": "Telmatherina celebensis", "dilaporkan": "Telmatherina", "tingkat": "genus",
    "nilai": "C", "skor": 3, "batas_D": "", "penyebab": ["referensi"],
    "peluang_belum_di_kamus": 1.0, "label_L3": ["kemungkinan endemik di luar kamus"],
    "keputusan": "wajib verifikasi"
  }],
  "kartu": {"asv07@MTN-ST2": {
    "keluaran": {"tingkat": "genus", "nilai": "C", "skor": "3/5", "galat_nilai": "0,7% (n=135; …)",
                 "peluang": "1,00", "catatan_peluang": "9 dari 9 Telmatherina di Kompleks Malili belum punya referensi", "penyebab": ["referensi"]},
    "alasan": [{"lapisan": "penamaan", "skor": null, "maks": null, "id": "…", "en": "…"},
               {"lapisan": "L1", "skor": 0, "maks": 2, "id": "…", "en": "…"}],
    "tindak_lanjut": "…",
    "asal_usul": {"status": "…", "jalur": "…", "sumber_dna": "…", "fasilitas": "…"},
    "batas_interpretasi": {"id": "Deteksi DNA bukan bukti pasti ikan hidup di lokasi.", "en": "…"}
  }},
  "celah": {
    "judul": "1 dari 19 ikan endemik Malili punya referensi 12S; 0 tervalidasi.",
    "kelompok": [{"label": "Telmatherinidae endemik", "petunjuk": "15 spesies", "total": 15, "ada_sekuens": 1, "tervalidasi": 0}],
    "per_genus": [{"wilayah": "Kompleks Malili", "genus": "Telmatherina", "n": 9, "r": 0, "p": 1.0}],
    "sumber": "mitohelper 12S Juli 2026; GBIF; checklist sementara"
  },
  "prioritas_barcode": [{"urutan": 1, "target": "Telmatherina antoniae", "jenis": "celah kamus", "danau": "Matano", "status_L3": "endemik", "klaim": 3}],
  "nama_ilmiah": ["Telmatherina", "Telmatherina celebensis", "…"],
  "ekspor": {"csv": "/api/runs/<id>/klaim.csv", "pdf": "/api/runs/<id>/laporan.pdf",
             "barcode": "/api/runs/<id>/prioritas_barcode.csv", "manifest": "/api/runs/<id>/manifest.json"}
}
```

- `kartu` disertakan penuh bila klaim ≤ 500; di atas itu kartu diambil per klaim (bagian 6).
- `nama_ilmiah` dipakai komponen `<SciText>` untuk memiringkan nama di teks alasan, sama seperti PDF.
- Pydantic → JSON Schema → tipe TypeScript (`json-schema-to-typescript`), dicek di CI agar dua sisi
  tidak berbeda.

## 5. Perubahan kecil di mesin Python (tanpa mengubah aturan)

| Berkas | Perubahan |
|---|---|
| `biotrace/dto.py` (baru) | `report_to_dto(report) -> dict`: menyusun kontrak di atas dari fungsi yang sudah ada, ditambah hitungan penyebab, chip, kelompok celah, deskripsi berkas |
| `biotrace/decision.py` | `origin()` mengembalikan 3 bagian terstruktur; kolom CSV `asal_usul` tetap gabungan kalimatnya |
| `biotrace/report.py` | `evidence_card()` menyertakan skor dan maks per lapisan sebagai angka, bukan hanya teks "(2/2)" |
| `biotrace/pipeline.py` | parameter `project_name`; catat `diproses` (tidak ikut di-hash) |
| `biotrace/__main__.py` | opsi `--json` untuk menulis `report.json` (mode statis) |
| `biotrace/api.py` (baru) | aplikasi FastAPI + run store |
| `requirements.txt` | `fastapi`, `uvicorn`, `python-multipart` |

## 6. API (FastAPI)

| Metode dan jalur | Fungsi |
|---|---|
| `POST /api/runs` | multipart: `bacaan`, `metadata`, `taksonomi?`, `fasta?`, `nama_proyek?` → jalankan mesin, simpan, kembalikan `{run_id}` |
| `POST /api/runs/demo` | jalankan skenario Matano SIMULASI |
| `GET /api/runs/{id}` | ReportDTO |
| `GET /api/runs/{id}/klaim?keputusan=&penyebab=&offset=&limit=` | baris klaim ringkas, tersaring dan berhalaman (proyek besar) |
| `GET /api/runs/{id}/klaim/{claim_id}` | satu Evidence Card |
| `GET /api/runs/{id}/klaim.csv`, `laporan.pdf`, `prioritas_barcode.csv`, `manifest.json` | ekspor dari run store |
| `GET /api/referensi` | metadata referensi dan peta kelengkapan |
| `GET /api/health` | versi aplikasi, referensi, aturan; BLAST+ tersedia atau tidak |

Proses dijalankan sinkron (200 sampel × 2.000 ASV ≈ 21 detik). Bila nanti lebih lama, ganti ke
antrean dengan status `GET /api/runs/{id}/status`.

## 7. Frontend (Next.js)

Struktur folder `web/`:

```
web/
  app/
    layout.tsx               font IBM Plex (next/font), token warna
    page.tsx                 unggah + "Muat demo Danau Matano (SIMULASI)"
    laporan/[runId]/page.tsx server component: ambil ReportDTO, render <Dashboard>
  components/
    Header.tsx  SimulationBanner.tsx  ReportTitle.tsx  MetaChips.tsx
    DecisionSummary.tsx  DecisionTile.tsx
    CauseBars.tsx  AuditTrail.tsx  MissingInfoCallout.tsx
    ClaimTable.tsx  FilterPills.tsx  ClaimRow.tsx
    EvidenceCard.tsx  LangToggle.tsx  OutputGrid.tsx  ReasonList.tsx  OriginList.tsx
    GapMap.tsx  BarcodePriority.tsx  Footer.tsx  UploadDialog.tsx  SciText.tsx
  lib/
    api.ts                   klien fetch; mode "live" (FastAPI) atau "static" (public/demo/report.json)
    types.ts                 dibangkitkan dari JSON Schema
    tokens.ts                warna keputusan dan nilai dari mockup
  public/demo/report.json    untuk mode statis
```

State interaksi disimpan di parameter URL agar bisa dibagikan dan tombol kembali berfungsi:
`/laporan/<id>?keputusan=wajib+verifikasi&klaim=asv07@MTN-ST2&bahasa=en`.

- Kartu ringkasan dan pil di tabel mengubah `keputusan`; baris tabel mengubah `klaim`;
  tombol ID/EN mengubah `bahasa` (hanya teks alasan, sesuai PRD; antarmuka tetap Bahasa Indonesia).
- Batang penyebab dan peta celah cukup CSS seperti di mockup; tidak perlu pustaka grafik.
- Tabel memakai grid CSS mockup; virtualisasi (TanStack Virtual) atau penomoran halaman dari API
  bila klaim > 300.
- Aksesibilitas mengikuti mockup: `aria-pressed` pada penyaring, target sentuh minimal 44 px,
  `role="note"` untuk banner SIMULASI.

Token desain dari mockup:

| Token | Nilai |
|---|---|
| latar / kartu / garis | `#F4F6F5` / `#FFFFFF` / `#D9E0DE` (garis dalam `#EDF1F0`) |
| teks / teks redup | `#12201D` / `#4A5A56` |
| aksen | `#0F6B63` (alternatif `#1D4E89`, `#7A3E9D`) |
| aman dilaporkan | tinta `#0F5E57`, latar `#E3F1EE`, garis `#A9D3CC` |
| dengan catatan | `#3F4B5C`, `#ECEFF3`, `#C7CED8` |
| wajib verifikasi | `#8A4100`, `#FCEBD9`, `#F0C18F` |
| jangan dipakai | `#8E1B3A`, `#F8E4EA`, `#E7AFC0` |
| banner SIMULASI | garis putus `#B9844D`, latar `#FFF8EF`, teks `#6B3A08` |
| huruf | IBM Plex Sans 15 px / 1,45; angka dan hash IBM Plex Mono |
| radius | kartu 12 px, tombol 8 px, chip 999 px; lebar maksimum 1280 px |

## 8. Pengujian

- **Python:** `report_to_dto()` lolos validasi JSON Schema; jumlah per keputusan di DTO sama
  dengan `klaim.csv`; ID run sama untuk input yang sama.
- **Kontrak:** tipe TypeScript dibangkitkan ulang di CI dan harus sama dengan yang di-commit.
- **Komponen (Vitest + Testing Library):** render dari `report.demo.json`; kartu penyaring mengubah
  isi tabel; memilih baris mengganti Evidence Card; ID/EN mengganti teks alasan.
- **Ujung ke ujung (Playwright):** unggah fixture `tests/fixtures/mini` → kalimat ringkasan sama
  dengan `ringkasan.kalimat`; unduh CSV → jumlah baris sama dengan tabel; tautan PDF berstatus 200.

## 9. Angka mockup vs hasil mesin

Mockup memakai angka contoh. Dashboard harus menampilkan hasil mesin, yang berbeda di beberapa
tempat:

| Di mockup | Hasil mesin sekarang | Alasan |
|---|---|---|
| 16 klaim dari 12 ASV | 15 klaim dari 10 ASV | skenario `make_demo.py` |
| *Telmatherina* P = 0,89; "8 dari 9 tanpa referensi" | P = 1,00; 9 dari 9 | sekuens *T. celebensis* tanpa voucher |
| Karper di kontrol → jangan dipakai | wajib verifikasi | matriks PRD: nilai D + label invasif |
| Galat per nilai: belum dikalibrasi | A 30,8%, B 11,8%, C 0,7%, D belum | hasil uji tahap 6 |
| Louhan dilaporkan "Kemungkinan louhan hibrida" | *Amphilophus citrinellus* + label "kemungkinan louhan hibrida" | label L3, bukan nama pengganti |
| Celah "1/15" | 1/15 ada sekuens, 0/15 tervalidasi | tampilkan dua tingkat |

## 10. Penerapan

- **Lokal (demo di laptop):** `uvicorn biotrace.api:app --port 8000` dan `npm run dev` di `web/`;
  `next.config` mengalihkan `/api/*` ke port 8000 sehingga tidak perlu CORS.
- **Satu perintah:** `docker compose up` dengan dua layanan (Python + `ncbi-blast+` dari apt; Node).
- **Statis untuk pitch:** `report.json` demo + `next build` (`output: "export"`) → hosting statis;
  unggah dinonaktifkan lewat `NEXT_PUBLIC_MODE=static`.
- **Privasi:** unggahan dan run store tetap lokal; tidak ada panggilan ke layanan luar; batas ukuran
  unggahan. Bila kelak ada peta, koordinat spesies terancam disamarkan (NFR PRD).

## 11. Tahapan implementasi

| Tahap | Isi | Selesai bila |
|---|---|---|
| D0 | `dto.py`, perubahan kecil mesin, `--json`, JSON Schema | DTO demo tervalidasi; uji Python lolos |
| D1 | FastAPI + run store + ekspor | unggah fixture mini lewat API mengembalikan DTO yang sama dengan CLI |
| D2 | kerangka Next.js, token, komponen statis dari `report.json` | halaman demo mirip mockup di 1440 px dan 375 px |
| D3 | interaksi: penyaring, pilih klaim, ID/EN, parameter URL | uji komponen lolos |
| D4 | halaman unggah + integrasi API + Playwright | uji ujung ke ujung dan uji kesamaan CSV/PDF lolos |
| D5 | docker compose, ekspor statis, README | demo jalan dengan satu perintah |

**Jalur cepat sebelum final submission:** D0 (hanya `--json`) + D2 + D3 dalam mode statis.
Dashboard demo bisa tampil untuk pitch tanpa server Python; unggah data nyata tetap lewat
Streamlit/CLI sampai D1 dan D4 selesai setelah hackathon.
