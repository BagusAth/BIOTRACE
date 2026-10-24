# Skenario demo Danau Matano — SIMULASI

**Data demo sintetis berlabel SIMULASI; bukan hasil lapangan.** Dibuat oleh `scripts/make_demo.py`
dengan `random.seed(2026)`. Setiap baris berkas memuat kolom `label_data = SIMULASI`, ID sampel
berawalan `SIM-`, dan header FASTA bertanda SIMULASI.

Desain: 3 stasiun (ST1-ST3) x 3 replikat di Danau Matano, satu kontrol negatif PCR per batch
ekstraksi (B1-B3). ST2 diberi fasilitas sekitar fiktif (keramba nila) untuk kalimat asal-usul.

| ASV | Isi | Asal urutan | Aksesi sumber | Substitusi | Harapan rencana | Hasil mesin |
|---|---|---|---|---:|---|---|
| asv01 | Nila | sekuens referensi nyata | MZ605472 | 0 | nama spesies; label invasif | MTN-ST1: Oreochromis niloticus (spesies), nilai B, aman dilaporkan, label invasif, penyebab marker; MTN-ST2: Oreochromis niloticus (spesies), nilai B, aman dilaporkan, label invasif, penyebab marker |
| asv02 | Gabus | sekuens referensi nyata | MN205549 | 0 | nama spesies; label invasif | MTN-ST1: Channa striata (spesies), nilai A, aman dilaporkan, label invasif |
| asv03 | Sapu-sapu | sekuens referensi nyata | KT239016 | 0 | nama spesies; label invasif | MTN-ST3: Pterygoplichthys (genus), nilai C, wajib verifikasi, label invasif, penyebab marker |
| asv04 | Karper | sekuens referensi nyata | LC069407 | 0 | nama spesies; label invasif; di ST1 juga ada di kontrol batch B1 -> batas maksimal D | MTN-ST1: Cyprinus carpio (spesies), nilai D, wajib verifikasi, label invasif, penyebab sampel; MTN-ST2: Cyprinus carpio (spesies), nilai A, aman dilaporkan, label invasif |
| asv05 | Amphilophus citrinellus (induk louhan) | sekuens referensi nyata | OQ681458 | 0 | kemungkinan louhan hibrida; invasif | MTN-ST1: Amphilophus citrinellus (spesies), nilai B, aman dilaporkan, label invasif; kemungkinan louhan hibrida, penyebab marker; MTN-ST2: Amphilophus citrinellus (spesies), nilai B, aman dilaporkan, label invasif; kemungkinan louhan hibrida, penyebab marker; MTN-ST3: Amphilophus citrinellus (spesies), nilai B, aman dilaporkan, label invasif; kemungkinan louhan hibrida, penyebab marker |
| asv06 | Telmatherina celebensis | sekuens referensi nyata | AP006772 | 0 | nama spesies bila referensinya tervalidasi; endemik | MTN-ST3: Telmatherina (genus), nilai B, aman dilaporkan, label kemungkinan endemik di luar kamus, penyebab referensi |
| asv07 | Telmatherina tak berreferensi | T. celebensis + substitusi acak berbenih | AP006772 | 5 | Telmatherina sp.; penyebab referensi; peluang belum di kamus; wajib verifikasi | MTN-ST2: Telmatherina (genus), nilai C, wajib verifikasi, label kemungkinan endemik di luar kamus, penyebab referensi; MTN-ST3: Telmatherina (genus), nilai C, wajib verifikasi, label kemungkinan endemik di luar kamus, penyebab referensi |
| asv08 | Urutan jauh | sekuens ikan + sekitar 8% substitusi | LC049786 | 14 | tidak dikenal; masuk daftar prioritas barcode | MTN-ST1: tidak dikenal (tidak dikenal), nilai D, dengan catatan, label kemungkinan endemik di luar kamus, penyebab referensi |
| asv09 | Dua Oryzias yang mirip | Oryzias dancena (12S identik dengan O. melastigma) | AB498069 | 0 | genus Oryzias; penyebab marker | MTN-ST3: Oryzias (genus), nilai C, wajib verifikasi, label kemungkinan endemik di luar kamus, penyebab referensi; marker; lokasi |
| asv10 | Sidat (ikan asli, sinyal lemah) | sekuens referensi nyata | MZ605514 | 0 | tambahan BioTrace: bacaan < 10 tanpa label L3 -> jangan dipakai | MTN-ST2: Anguilla marmorata (spesies), nilai D, jangan dipakai, penyebab referensi; sampel |

**Ringkasan keputusan:** Dari 15 klaim, 8 aman dilaporkan, 1 dengan catatan, 5 wajib verifikasi, 1 jangan dipakai; 1 tidak dikenal.

## Perbedaan dari harapan rencana dan alasannya

- *Telmatherina celebensis* dilaporkan sebagai genus *Telmatherina*: kedua sekuensnya di GenBank
  tidak punya `specimen_voucher`, jadi belum tervalidasi. Peluang belum di kamus untuk *Telmatherina*
  di Kompleks Malili = 1,00 (bukan 0,89, yang mengandaikan sekuens itu tervalidasi).
- Sapu-sapu dilaporkan sebagai genus *Pterygoplichthys* (penyebab marker): amplikon MiFish
  *P. pardalis* identik dengan *P. anisitsi* dan *P. disjunctivus* di referensi.
- Karper di ST1 terkena batas D karena muncul di kontrol batch B1. Karper berlabel invasif, dan
  matriks keputusan PRD menetapkan nilai D dengan label L3 sebagai **wajib verifikasi** (ikan invasif
  C-D tidak dijadikan dasar pemberantasan sebelum dicek). Cabang **jangan dipakai** ditunjukkan oleh
  sidat (asv10): ikan asli tanpa label L3, bacaan di bawah 10.

## Membuat ulang

```bash
.venv/Scripts/python scripts/make_demo.py
```

Sidik jari laporan demo: `sha256:10325c7c8571accc4fa8af7edd2fdd586ee209eb52005db1579fe5643eb4dd39`
