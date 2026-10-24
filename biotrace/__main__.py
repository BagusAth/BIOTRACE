"""Baris perintah: python -m biotrace run --reads ... --metadata ... [--taxonomy ...] [--fasta ...] --out out/"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from .config import load_rules
from .dto import report_to_dto, write_json
from .pipeline import run
from .reference import load_reference
from .report import write_outputs


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="biotrace")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="periksa satu proyek eDNA")
    r.add_argument("--reads", required=True, type=Path)
    r.add_argument("--metadata", required=True, type=Path)
    r.add_argument("--taxonomy", type=Path)
    r.add_argument("--fasta", type=Path)
    r.add_argument("--rules", type=Path)
    r.add_argument("--reference", type=Path, help="folder referensi (bawaan data/ref/v0.1)")
    r.add_argument("--mode", choices=["proyek", "uji"], default="proyek")
    r.add_argument("--simulation", action="store_true", help="tandai data sebagai SIMULASI")
    r.add_argument("--threads", type=int, default=1)
    r.add_argument("--out", type=Path, default=Path("out"))
    r.add_argument("--project-name", default="", help="nama proyek untuk tampilan (tidak ikut sidik jari)")
    r.add_argument("--json", action="store_true",
                   help="tulis juga report.json (kontrak biotrace.report.v1) untuk dashboard")
    args = ap.parse_args(argv)

    report = run(args.reads, args.metadata, args.taxonomy, args.fasta,
                 rules=load_rules(args.rules) if args.rules else None,
                 reference=load_reference(args.reference) if args.reference else None,
                 mode=args.mode, threads=args.threads, simulation=args.simulation,
                 project_name=args.project_name)
    write_outputs(report, args.out)
    if args.json:
        stamp = dt.datetime.now().astimezone().isoformat(timespec="seconds")
        print(f"kontrak data: {write_json(report_to_dto(report, processed_at=stamp), args.out / 'report.json')}")
    print(report.summary_sentence())
    print(f"sidik jari laporan: sha256:{report.fingerprint}")
    print(f"waktu proses: {report.seconds:.1f} dtk -> {args.out}")


if __name__ == "__main__":
    main()
