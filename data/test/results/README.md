# Hasil uji mesin v0.1 (tahap 6)

Dibuat oleh `scripts/run_engine_tests.py` (24 Okt 2026, aturan `rules_v0.1.yaml`, BLAST+ 2.17.0).
Semua angka adalah **uji logika mesin pada data publik**, bukan validasi lapangan di Malili.

| Berkas | Isi |
|---|---|
| `results_v0.1.csv` | semua metrik (format panjang: uji, referensi, aturan, metrik, nilai, target, catatan) |
| `loo_malili_aturan_penuh.csv`, `loo_malili_logika.csv` | uji tanpa-satu-spesies per kueri, referensi kandidat Malili |
| `loo_imarfish.csv` | uji tanpa-satu-spesies per kueri, I-MarFish LocalDB |
| `loo_lake_st_pierre.csv` | uji tanpa-satu-spesies per kueri, referensi Kanada |
| `galat_per_nilai.csv` | galat per nilai A-D untuk F19 (dibaca mesin lewat `calibration.error_by_grade_file`) |
| `lake_st_pierre.json`, `lsp_klaim.csv`, `lsp_proyek_uji/` | mode uji F27 dengan tabel deteksi Lake St. Pierre |

## 6.1 Uji tanpa-satu-spesies (F26)

Kueri = amplikon MiFish-U dari tiap sekuens bernama spesies (satu per pasangan spesies-urutan).
Spesies kueri disembunyikan, lalu sisa kecocokan dinilai. "Nama keliru lolos" untuk ambang 97% =
kecocokan teratas yang tersisa >= 97%; untuk BioTrace = klaim tingkat spesies yang bernilai A-B
dengan asumsi L2 = 1 dan L4 = 2 (batas atas, karena simulasi tidak punya sinyal lapangan).

| Referensi | Kueri | Ambang 97% | BioTrace | BioTrace bernilai A | Turun ke genus/tidak dikenal |
|---|---:|---:|---:|---:|---:|
| Kandidat Malili, aturan penuh (validasi + tercatat) | 252 | 70,2% | **6,0%** | 4,4% | 94,0% |
| Kandidat Malili, logika saja (semua dianggap tervalidasi) | 252 | 70,2% | 26,6% | 14,7% | 73,4% |
| I-MarFish LocalDB (ikan laut), logika saja | 3.499 | 43,6% | 26,0% | 15,8% | 74,0% |

Target PRD (< 16%) tercapai dengan aturan penuh. Dengan logika saja (tanpa syarat voucher),
BioTrace tetap memangkas nama keliru, tetapi masih di atas target; kontributor terbesar adalah
genus dengan 12S yang sangat mirip antarspesies (*Oreochromis* 48%, *Oryzias* 35%), sedangkan
*Channa* 6,5%. Angka ini berbeda dari simulasi lama di PRD (52% vs 16%) karena definisi
kueri dan versi I-MarFish berbeda; catat keduanya saat dikutip.

Galat per nilai (aturan penuh, Malili): A 30,8% (n=39), B 11,8% (n=34), C 0,7% (n=135),
D belum terkalibrasi (n=0). Galat A tinggi karena di simulasi L2/L4 diasumsikan maksimal.

## 6.2 Mode uji Lake St. Pierre (F27)

`edna_lg_clean.csv` hanya berisi deteksi per spesies (tanpa urutan ASV), jadi dipakai **jalur
kedua**: uji tanpa-satu-spesies pada referensi Kanada (`data/test/lake_st_pierre/ref`, 112 dari 118
spesies wilayah punya 12S), lalu tabel deteksi dan electrofishing untuk L2, L4, dan sebaran keputusan.

- **Spesies terhapus yang tidak diberi nama lain: 91,9%** (333 kueri, 107 spesies; target >= 90%).
  Ambang 97% memberi nama keliru pada 78,7% kueri.
- Presisi klaim A-B terhadap electrofishing **tidak bisa dihitung**: tiap lokasi di tabel Dryad
  hanya punya 1 replikat (ronde 2 tahun 2022 memakai kode situs berbeda) dan tanpa kontrol
  negatif, sehingga L4 = 0 dan tidak ada klaim A-B. Pelengkap: 57 dari 173 klaim tingkat spesies
  (32,9%) cocok dengan tangkapan electrofishing di sektor dan tahun yang sama. Electrofishing juga
  melewatkan spesies, jadi angka ini batas bawah.
- Sebaran keputusan proyek uji: 111 dengan catatan, 231 jangan dipakai (342 klaim); 133 klaim
  bacaannya di bawah ambang data nyasar.

## 6.3 Uji sinyal lab (Li dkk. 2019)

Tabel Li dkk. 2019 belum ada di repo (`data/test/li2019/`). `tag_jump_fraction` tetap 0,001 dan
ditandai **belum dikalibrasi** di aturan dan di setiap laporan.
