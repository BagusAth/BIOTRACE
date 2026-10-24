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

## Uji

```bash
.venv/Scripts/python -m pytest
```

## Sitasi data

mitohelper (Lim & Thompson 2021, *Environmental DNA*), NCBI GenBank, MitoFish,
DBP Metabarcoding Pipeline / I-MarFish (GPL-3.0), Lake St. Pierre (Astorg dkk. 2025,
Dryad 10.5061/dryad.3bk3j9kzf), GBIF, FEOW, Herder dkk. 2006, Hedianto & Sentosa 2019,
Permen KP No. 19/2020, IUCN Red List.
