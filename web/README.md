# Dashboard BioTrace (mode statis)

Dashboard satu halaman untuk laporan verifikasi eDNA, mengikuti mockup "Dashboard verifikasi
eDNA · satu halaman" dan rancangan di `../docs/rancangan_dashboard.md` (jalur cepat D0, D2, D3).

Semua angka berasal dari `public/demo/report.json` (kontrak `biotrace.report.v1` yang dibuat
`biotrace/dto.py`). Dashboard tidak menghitung ulang nilai, penyebab, atau keputusan.

## Menjalankan

Bangkitkan data demo Matano (SIMULASI) dari mesin Python, dari folder akar repo:

```bash
.venv/Scripts/python scripts/build_dashboard_data.py
```

Lalu di folder `web/`:

```bash
npm install
npm run dev        # pengembangan, http://localhost:3000
npm run build      # ekspor statis ke out/
```

Isi `out/` bisa dihosting di server statis mana pun. Untuk subfolder (mis. GitHub Pages), set
`NEXT_PUBLIC_BASE_PATH=/nama-repo` saat build.

## Interaksi

- Kartu keputusan dan pil di tabel menyaring klaim; baris tabel mengganti Evidence Card;
  tombol ID/EN mengganti bahasa teks alasan.
- State disimpan di URL, misalnya `/?keputusan=wajib+verifikasi&klaim=asv07%40MTN-ST2&bahasa=en`,
  sehingga tampilan bisa dibagikan.
- Tombol "Unggah data" nonaktif di mode statis; unggah data nyata lewat Streamlit (`app.py`)
  atau `python -m biotrace run ... --json`.

## Uji

```bash
npm test           # Vitest + Testing Library
npm run typecheck  # termasuk memeriksa report.json terhadap lib/types.ts
npm run lint
```

## Struktur

```
app/page.tsx              membaca public/demo/report.json saat build
components/Dashboard.tsx  merangkai semua blok
components/*.tsx          Header, SimulationBanner, ReportTitle, DecisionSummary, CauseBars,
                          AuditTrail, ClaimTable, EvidenceCard, GapMap, BarcodePriority, Footer
lib/types.ts              tipe kontrak biotrace.report.v1
lib/state.ts              state penyaring/pilihan/bahasa dan kodek URL
lib/useDashboardState.ts  sinkronisasi state dengan URL (useSyncExternalStore)
lib/tokens.ts             warna keputusan dan nilai dari mockup
```
