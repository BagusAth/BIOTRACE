"""Normalisasi nama ilmiah: kunci spesies binomial, genus, dan tingkat takson bersama."""

from __future__ import annotations

import re

UNRESOLVED_EPITHETS = {"sp", "sp.", "spp", "spp.", "cf", "cf.", "aff", "aff.", "nr", "nr."}
HYBRID = re.compile(r"\s+x\s+|\s+×\s+")


def clean(name: str) -> str:
    return " ".join(str(name or "").replace("_", " ").split())


def is_hybrid(name: str) -> bool:
    return bool(HYBRID.search(clean(name)))


def species_key(name: str) -> tuple[str, bool]:
    """Kembalikan (kunci, terselesaikan).

    Kunci binomial untuk nama spesies biasa (subspesies dan varietas dilebur ke spesiesnya).
    Nama hibrida, "sp.", "cf.", atau "aff." tidak terselesaikan sampai spesies: kuncinya nama
    lengkap, dan nama seperti itu tidak boleh mendukung klaim tingkat spesies.
    """
    n = clean(name)
    if not n:
        return "", False
    if is_hybrid(n):
        return n, False
    parts = n.split(" ")
    if len(parts) < 2 or not parts[0][:1].isupper():
        return n, False
    epithet = parts[1]
    if epithet.lower() in UNRESOLVED_EPITHETS or not epithet.isalpha() or not epithet.islower():
        return n, False
    return f"{parts[0]} {epithet}", True


def genus_of(name: str) -> str:
    n = clean(name)
    return n.split(" ")[0] if n else ""


def genera_of(name: str) -> list[str]:
    """Genus untuk nama biasa, atau genus kedua induk untuk hibrida."""
    n = clean(name)
    if is_hybrid(n):
        return sorted({genus_of(p) for p in HYBRID.split(n) if p.strip()})
    return [genus_of(n)] if n else []


def same_species_name(a: str, b: str) -> bool:
    """Bandingkan dua nama binomial dengan toleransi akhiran epitet (multitaeniata/-us)."""
    ka, ra = species_key(a)
    kb, rb = species_key(b)
    if not (ra and rb):
        return clean(a) == clean(b)
    ga, ea = ka.split(" ")
    gb, eb = kb.split(" ")
    if ga != gb:
        return False
    stem = min(len(ea), len(eb), max(len(ea), len(eb)) - 2)
    return ea == eb or (stem >= 5 and ea[:stem] == eb[:stem])
