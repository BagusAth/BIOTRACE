"""Bangkitkan data dashboard statis dari skenario demo Matano (SIMULASI).

Menulis report.json (kontrak biotrace.report.v1) beserta berkas ekspor (klaim.csv,
laporan.pdf, prioritas_barcode.csv, manifest.json) ke web/public/demo/, lalu
`npm run build` di web/ mengemasnya menjadi situs statis.

    python scripts/build_dashboard_data.py
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from biotrace.config import ROOT  # noqa: E402
from biotrace.dto import report_to_dto, write_json  # noqa: E402
from biotrace.pipeline import run  # noqa: E402
from biotrace.report import write_outputs  # noqa: E402

DEMO = ROOT / "data" / "demo" / "matano"
OUT = ROOT / "web" / "public" / "demo"


def main() -> None:
    report = run(DEMO / "bacaan.csv", DEMO / "metadata.csv", DEMO / "taksonomi.csv", DEMO / "asv.fasta",
                 project_name="Pemantauan Danau Matano")
    write_outputs(report, OUT)
    (OUT / "ringkasan.json").unlink(missing_ok=True)   # isinya sudah ada di report.json
    stamp = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    path = write_json(report_to_dto(report, processed_at=stamp), OUT / "report.json")
    print(report.summary_sentence())
    print(f"sidik jari laporan: sha256:{report.fingerprint}")
    print(f"data dashboard -> {path.parent}")


if __name__ == "__main__":
    main()
