# Angka untuk pitch — BioTrace Indonesia v0.1

Dibuat oleh `scripts/pitch_numbers.py`. **Label di slide: data demo sintetis; angka simulasi diberi keterangan referensi yang dipakai.** Angka uji adalah uji logika mesin pada data publik, bukan validasi lapangan di Malili.

| Angka | Sumber | Dipakai di slide |
|---|---|---|
| 1 dari 19 endemik Malili punya referensi 12S; 14 dari 15 telmatherinid tidak | Audit Dataset, dibangun ulang di `data/ref/v0.1/kelengkapan_spesies.csv` | Masalah, referensi |
| 0 dari 19 endemik punya 12S tervalidasi (sekuens *T. celebensis* tanpa voucher) | `data/ref/v0.1/ref12S_taksonomi.csv` (GenBank specimen_voucher) | Masalah, referensi |
| Nama keliru lolos, kandidat Malili: ambang 97% 70,2% vs aturan BioTrace 6,0% (logika tanpa syarat voucher 26,6%) | Tahap 6.1, `data/test/results/results_v0.1.csv`, referensi kandidat Malili v0.1 | Bukti |
| Nama keliru lolos, I-MarFish (ikan laut): ambang 97% 43,6% vs BioTrace 26,0% | Tahap 6.1, I-MarFish LocalDB (DBP UNDIP) | Bukti |
| Spesies terhapus yang tidak diberi nama lain: 91,9% (ambang 97% memberi nama keliru 78,7%) | Tahap 6.2, referensi Kanada untuk Lake St. Pierre | Bukti |
| Presisi A-B vs electrofishing: tidak bisa dihitung (1 replikat per lokasi, tanpa kontrol); pelengkap 57 dari 173 klaim spesies (32,9%) cocok, batas bawah | Tahap 6.2, `data/test/results/lake_st_pierre.json` | Bukti |
| Waktu unggah sampai ringkasan: 21,2 detik untuk 200 sampel x 2.000 ASV (24.423 klaim, termasuk BLAST); 0,5 detik (skenario Matano, 15 klaim) | Log aplikasi (`Report.seconds`), `scripts/benchmark.py` | Demo |
| Skenario Matano (SIMULASI): 15 klaim — 8 aman dilaporkan, 1 dengan catatan, 5 wajib verifikasi, 1 jangan dipakai; 1 tidak dikenal | Hasil demo, `data/demo/matano/hasil/ringkasan.json` | Demo |

Galat per nilai (F19, simulasi tanpa-satu-spesies ref Malili; L2/L4 diasumsikan maksimal):

- Nilai A: 30,8% (n=39; uji tanpa-satu-spesies ref Malili v0.1)
- Nilai B: 11,8% (n=34; uji tanpa-satu-spesies ref Malili v0.1)
- Nilai C: 0,7% (n=135; uji tanpa-satu-spesies ref Malili v0.1)
- Nilai D: belum dikalibrasi (n=0)

`tag_jump_fraction` belum dikalibrasi: tabel Li dkk. 2019 belum ada di repo.
