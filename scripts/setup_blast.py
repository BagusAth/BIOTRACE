"""Pasang BLAST+ dari penginstal resmi NCBI ke tools/ (Windows), lalu cek blastn -version.

Di Linux/macOS pakai conda (lihat environment.yml) atau paket sistem; skrip ini hanya
memeriksa versinya.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from biotrace.config import TOOLS_DIR, find_blast_tool  # noqa: E402

VERSION = "2.17.0"
BASE = "https://ftp.ncbi.nlm.nih.gov/blast/executables/blast+/" + VERSION + "/"
TARBALL = f"ncbi-blast-{VERSION}+-x64-win64.tar.gz"


def download(url: str, dest: Path) -> None:
    print(f"unduh {url}")
    with urllib.request.urlopen(url) as r, open(dest, "wb") as fh:
        while chunk := r.read(1 << 20):
            fh.write(chunk)


def install_windows() -> None:
    TOOLS_DIR.mkdir(exist_ok=True)
    tar_path = TOOLS_DIR / TARBALL
    if not tar_path.exists():
        download(BASE + TARBALL, tar_path)
    expected = urllib.request.urlopen(BASE + TARBALL + ".md5").read().decode().split()[0]
    md5 = hashlib.md5(tar_path.read_bytes()).hexdigest()
    if md5 != expected:
        tar_path.unlink()
        raise SystemExit(f"MD5 {TARBALL} tidak cocok ({md5} != {expected}); unduh ulang")
    with tarfile.open(tar_path) as tf:
        tf.extractall(TOOLS_DIR, filter="data")
    print(f"BLAST+ {VERSION} terpasang di {TOOLS_DIR}")


def main() -> None:
    if find_blast_tool("blastn") is None:
        if os.name != "nt":
            raise SystemExit("blastn tidak ditemukan; pasang lewat: conda install -c bioconda blast")
        install_windows()
    for tool in ("blastn", "makeblastdb"):
        exe = find_blast_tool(tool)
        if exe is None:
            raise SystemExit(f"{tool} tidak ditemukan")
        out = subprocess.run([exe, "-version"], capture_output=True, text=True, check=True)
        print(out.stdout.strip().splitlines()[0], "->", exe)


if __name__ == "__main__":
    main()
