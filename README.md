# BioTrace Indonesia

> Biodiversitas Indonesia, dibaca dengan data Indonesia.

BioTrace memeriksa setiap nama ikan dalam hasil eDNA sebelum masuk laporan, memakai
referensi ikan Indonesia yang tervalidasi, dan menyatakan seberapa yakin nama itu boleh
dipakai. Bila tidak ada referensi yang cocok, BioTrace melaporkan **"tidak dikenal"**,
bukan memberi nama ikan lain.

Implementasi ini mengikuti dokumen *BioTrace Indonesia — Rencana Implementasi PRD v2*
(tahap 0–7). Wilayah fokus MVP: kompleks Danau Malili (Matano, Mahalona, Towuti),
marker 12S rRNA (MiFish-U).

## Persiapan lingkungan (tahap 0)

Dengan conda (Linux/macOS/WSL):

```bash
conda env create -f environment.yml
conda activate biotrace
blastn -version
```

Di Windows tanpa conda:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python scripts/setup_blast.py
```

`scripts/setup_blast.py` mengunduh BLAST+ 2.17.0 dari penginstal resmi NCBI ke `tools/`
(dicek MD5-nya). Lokasi lain bisa diberikan lewat variabel `BIOTRACE_BLAST_BIN`.

Unduh semua berkas sumber ke `data/raw/` dan catat di manifest:

```bash
.venv/Scripts/python scripts/fetch_raw.py --malili-zip ../GENOHACK/biotrace_ref_malili_v0.1.zip --dryad-zip ../GENOHACK/doi_10_5061_dryad_3bk3j9kzf__v20250924.zip
```

Berkas GitHub (mitohelper, DBP/I-MarFish) dipatok ke nomor commit. Dari arsip Dryad Lake
St. Pierre hanya lima CSV kecil dan README yang diambil, tanpa `raw_seq.zip` (2,94 GB).
`data/raw/` tidak di-commit; isinya bisa diunduh ulang dan dicek dengan SHA-256 di
`data/ref/v0.1/manifest.csv`.

## Tahap implementasi

| Tahap | Kebutuhan PRD | Isi | Berkas utama |
|---|---|---|---|
| 0. Persiapan | — | lingkungan, BLAST+, manifest data, aturan v0.1 | `scripts/setup_blast.py`, `scripts/fetch_raw.py`, `rules/rules_v0.1.yaml` |
| 1. Referensi | F5–F7 | referensi 12S Malili tervalidasi, checklist, status, alias, kelengkapan | `scripts/build_reference.py`, `biotrace/reference.py`, `data/ref/v0.1/` |
| 2. Input dan jejak | F1–F4 | baca 3 CSV + FASTA, validasi, sidik jari | `biotrace/io.py`, `biotrace/provenance.py` |
| 3. Penamaan dan audit | F8–F15 | BLAST, tingkat nama, "tidak dikenal", L1–L4 | `biotrace/naming.py`, `biotrace/audit.py` |
| 4. Penilaian dan keputusan | F16–F21 | nilai A–D, penyebab, peluang belum di kamus, keputusan, asal-usul | `biotrace/scoring.py`, `biotrace/decision.py`, `biotrace/pipeline.py` |
| 5. Keluaran | F22–F25 | ringkasan, Evidence Card, PDF, CSV, prioritas barcode, Streamlit | `biotrace/report.py`, `app.py` |
| 6. Uji mesin | F26–F27 | uji tanpa-satu-spesies, mode uji Lake St. Pierre | `biotrace/simulate.py`, `scripts/run_engine_tests.py`, `data/test/results/` |
| 7. Demo dan bukti | — | skenario Matano berlabel SIMULASI, angka pitch | `scripts/make_demo.py`, `data/demo/matano/`, `docs/angka_pitch.md` |

Temuan utama (rincian di `docs/angka_pitch.md` dan `data/test/results/README.md`):

- 1 dari 19 endemik Malili punya sekuens 12S, dan sekuens itu (*T. celebensis*) tanpa voucher,
  jadi 0 dari 19 tervalidasi.
- Uji tanpa-satu-spesies pada kandidat Malili: ambang 97% meloloskan 70,2% nama keliru, aturan
  BioTrace 6,0%. Lake St. Pierre: 91,9% spesies terhapus tidak diberi nama lain.
- `tag_jump_fraction` belum dikalibrasi (tabel Li dkk. 2019 belum ada di repo).

## Struktur

```
data/ref/v0.1/          referensi 12S, checklist, status, alias, jalur masuk, kelengkapan, manifest
data/test/lake_st_pierre/  berkas Dryad + referensi Kanada terpisah
data/test/li2019/       tabel bacaan dengan kontrol (bila tersedia)
data/demo/matano/       skenario berlabel SIMULASI
rules/rules_v0.1.yaml   semua ambang dan parameter
biotrace/               modul mesin (io, provenance, reference, naming, audit, scoring, decision, report, simulate)
scripts/                skrip data dan uji
tests/                  uji per aturan dengan data kecil
app.py                  antarmuka Streamlit
```

## Menjalankan

Antarmuka Streamlit (5 halaman: unggah, ringkasan keputusan, tabel klaim, Evidence Card,
peta celah; ekspor PDF, CSV, prioritas barcode, manifest di sidebar):

```bash
.venv/Scripts/python -m streamlit run app.py
```

Baris perintah:

```bash
.venv/Scripts/python -m biotrace run --reads bacaan.csv --metadata metadata.csv --fasta asv.fasta --out out/
```

Keluaran di `out/`: `klaim.csv` (skema keluaran PRD), `prioritas_barcode.csv`,
`laporan.pdf` (Bahasa Indonesia), `manifest.json` (SHA-256 input, versi referensi dan aturan,
sidik jari laporan), `ringkasan.json`. Tambahkan `--json` untuk menulis `report.json`
(kontrak `biotrace.report.v1` untuk dashboard) dan `--project-name` untuk nama proyek di tampilan.

Uji kinerja (200 sampel, 2.000 ASV, termasuk BLAST): `scripts/benchmark.py` — sekitar 21 detik
di laptop pengembang.

Demo dan bukti (tahap 6–7):

```bash
.venv/Scripts/python scripts/build_test_ref.py
.venv/Scripts/python scripts/run_engine_tests.py
.venv/Scripts/python scripts/make_demo.py
.venv/Scripts/python scripts/pitch_numbers.py
```

Dashboard satu halaman (Next.js, mode statis) untuk pitch ada di `web/`; lihat `web/README.md`:

```bash
.venv/Scripts/python scripts/build_dashboard_data.py
cd web && npm install && npm run build
```

Di aplikasi, tombol **Muat demo Danau Matano (SIMULASI)** menjalankan skenario demo. Data yang
membawa kolom `label_data = SIMULASI` otomatis ditandai SIMULASI di layar, kartu, dan PDF.

## Uji

```bash
.venv/Scripts/python -m pytest
```

## Sitasi data

mitohelper (Lim & Thompson 2021, *Environmental DNA*), NCBI GenBank, MitoFish,
DBP Metabarcoding Pipeline / I-MarFish (GPL-3.0), Lake St. Pierre (Astorg dkk. 2025,
Dryad 10.5061/dryad.3bk3j9kzf), GBIF, FEOW, Herder dkk. 2006, Hedianto & Sentosa 2019,
Permen KP No. 19/2020, IUCN Red List.
