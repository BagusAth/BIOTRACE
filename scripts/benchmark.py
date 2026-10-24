"""Uji kinerja US1: proyek 200 sampel dan 2.000 ASV dari unggah sampai ringkasan < 2 menit.

Membuat proyek sintetis (berlabel SIMULASI) dari sekuens referensi dengan mutasi acak
berbenih tetap, lalu menjalankan mesin penuh termasuk BLAST.

    python scripts/benchmark.py --samples 200 --asvs 2000
"""

from __future__ import annotations

import argparse
import random
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from biotrace.config import load_rules  # noqa: E402
from biotrace.pipeline import run  # noqa: E402
from biotrace.reference import load_reference, read_fasta  # noqa: E402

BASES = "ACGT"


def mutate(seq: str, rate: float, rng: random.Random) -> str:
    return "".join(rng.choice([b for b in BASES if b != c]) if rng.random() < rate else c for c in seq)


def make_project(out: Path, n_samples: int, n_asvs: int, seed: int = 2026) -> dict[str, Path]:
    rng = random.Random(seed)
    ref = load_reference()
    seqs = read_fasta(ref.root / "ref12S.fasta")
    pool = sorted(a for a, s in seqs.items() if len(s) >= 400)
    asvs = {}
    for i in range(n_asvs):
        s = seqs[rng.choice(pool)]
        start = rng.randrange(0, len(s) - 180)
        asvs[f"asv{i:05d}"] = mutate(s[start:start + 175], rng.choice([0, 0, 0.01, 0.03, 0.08]), rng)
    n_sites = n_samples // 3
    samples = [f"S{site:03d}{rep}" for site in range(n_sites) for rep in "ABC"]
    samples += [f"S{n_sites:03d}{r}" for r in "ABC"][: n_samples - len(samples)]
    controls = [f"NEG{b}" for b in range(1, 6)]
    lines = ["asv_id,sample_id,reads"]
    for asv in sorted(asvs):
        for smp in rng.sample(samples, k=max(3, n_samples // 15)):
            lines.append(f"{asv},{smp},{rng.randint(1, 5000)}")
        if rng.random() < 0.05:
            lines.append(f"{asv},{rng.choice(controls)},{rng.randint(1, 50)}")
    (out / "bacaan.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    meta = ["sample_id,site_id,latitude,longitude,collection_date,sample_type,replicate,extraction_batch,marker,lake"]
    for i, smp in enumerate(samples):
        meta.append(f"{smp},ST{smp[1:4]},-2.48,121.35,2026-08-01,sampel,{smp[-1]},B{1 + i % 5},12S MiFish-U,Matano")
    for b, ctl in enumerate(controls, start=1):
        meta.append(f"{ctl},NEG,,,2026-08-01,kontrol_negatif_pcr,1,B{b},12S MiFish-U,Matano")
    (out / "metadata.csv").write_text("\n".join(meta) + "\n", encoding="utf-8")
    (out / "asv.fasta").write_text("".join(f">{a}\n{s}\n" for a, s in sorted(asvs.items())), encoding="utf-8")
    return {"reads": out / "bacaan.csv", "metadata": out / "metadata.csv", "fasta": out / "asv.fasta"}


def benchmark(n_samples: int = 200, n_asvs: int = 2000, threads: int = 2):
    with tempfile.TemporaryDirectory() as tmp:
        files = make_project(Path(tmp), n_samples, n_asvs)
        report = run(files["reads"], files["metadata"], fasta=files["fasta"], rules=load_rules(),
                     reference=load_reference(), threads=threads, simulation=True)
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--samples", type=int, default=200)
    ap.add_argument("--asvs", type=int, default=2000)
    ap.add_argument("--threads", type=int, default=2)
    args = ap.parse_args()
    report = benchmark(args.samples, args.asvs, args.threads)
    print(f"{args.samples} sampel, {args.asvs} ASV, {len(report.claims)} klaim: {report.seconds:.1f} detik")
    print(report.summary_sentence())


if __name__ == "__main__":
    main()
