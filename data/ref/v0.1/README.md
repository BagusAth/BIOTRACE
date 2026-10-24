# Referensi BioTrace v0.1 — Kompleks Danau Malili (12S)

Dibangun oleh `scripts/build_reference.py` dari berkas di `data/raw/` (lihat `manifest.csv`).
Hanya sekuens **tervalidasi** dari spesies yang **tercatat di Indonesia** yang boleh mendukung
klaim tingkat spesies.

| Berkas | Isi |
|---|---|
| `ref12S.fasta` | 896 sekuens kandidat 12S dari 226 nama (204 takson setelah normalisasi) |
| `ref12S_taksonomi.csv` | aksesi, taksonomi, sumber, voucher, status validasi, tercatat_di_indonesia, tanggal masuk |
| `aksesi_dicek.csv` | aksesi yang dicek ke GenBank beserta specimen_voucher, country, isolate |
| `checklist_malili.csv` | spesies per danau (Matano, Mahalona, Towuti) atau tingkat wilayah, dengan sumber dan tahun |
| `status.csv` | kategori IUCN (lewat GBIF), status Permen KP 19/2020, status invasif dan sumbernya |
| `alias.csv` | spesies dan genus induk louhan dipetakan ke "louhan hibrida" |
| `jalur_masuk.csv` | jalur introduksi dan kemungkinan sumber DNA lain |
| `kelengkapan.csv` | per genus dan wilayah: n, r, P belum di kamus |
| `kelengkapan_spesies.csv` | ketersediaan 12S per spesies checklist |
| `manifest_sha256.txt` | SHA-256 semua berkas referensi |
| `sumber/invasif.csv` | daftar invasif bersumber, masukan untuk `status.csv` |

## Aturan v0.1

- **tercatat_di_indonesia**: `ya` bila ada di checklist Malili atau daftar introduksi, atau GBIF
  mencatat kemunculan dengan `country=ID`; `tidak` bila GBIF mencatat 0; `belum dicek` untuk nama
  yang belum sampai spesies (hibrida, "sp.", "cf.").
- **status_validasi**: `tervalidasi` bila catatan GenBank punya `specimen_voucher` dan nama
  organisme GenBank sama dengan nama di mitohelper; selain itu `belum tervalidasi`
  (alasan dicatat di `alasan_validasi`).
- **Kelengkapan**: P = (n − r) / n; n = spesies genus di checklist wilayah, r = yang punya minimal
  satu sekuens tervalidasi. Mesin memakai tingkat wilayah (Kompleks Malili) sesuai
  `reference.completeness_scope` di aturan; tingkat danau tetap dihitung untuk peta celah.

## Temuan saat dibangun (24 Okt 2026)

- 1 dari 19 endemik Malili punya sekuens 12S (*Telmatherina celebensis*); 14 dari 15
  telmatherinid tidak punya — sama dengan Audit Dataset.
- Kedua sekuens *T. celebensis* (AP006772, LC104423) **tidak punya specimen_voucher**, jadi
  belum tervalidasi: 0 dari 19 endemik punya 12S tervalidasi dan P *Telmatherina* = 1,0
  (bukan 0,89). Klaim *Telmatherina* turun ke genus dengan penyebab "referensi".
- 398 dari 896 sekuens tervalidasi; 7 sekuens ditolak karena nama GenBank berbeda
  (mis. LC049784 tercatat *Glossogobius giuris* di mitohelper, *Awaous gutum* di GenBank).

## Batas dan pekerjaan tinjauan ahli

- Checklist dan sebaran per danau masih **sementara**. GBIF menerima 18 spesies
  Telmatherinidae (termasuk *T. albolabiosus*), Audit Dataset memakai 17; *Oryzias marmoratus*
  dan *O. profundicola* (Towuti) perlu dikonfirmasi sebagai endemik Malili sebelum masuk.
- Kolom `permen_kp_19_2020` belum dicek terhadap lampiran peraturan.
- Kemunculan GBIF di Indonesia bisa mencakup catatan budidaya atau akuarium.
