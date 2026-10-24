"""Templat alasan dua bahasa (Indonesia dan Inggris) untuk Evidence Card dan tabel klaim."""

from __future__ import annotations


def pct(x: float | None, lang: str = "id") -> str:
    if x is None:
        return "-"
    s = f"{x:.1f}"
    return s.replace(".", ",") if lang == "id" else s


def frac(x: float | None, lang: str = "id") -> str:
    if x is None:
        return "-"
    s = f"{x:.2f}"
    return s.replace(".", ",") if lang == "id" else s


def naming_reason(name: str, n_species: int, lang: str) -> str:
    if lang == "id":
        return f"Dilaporkan sebagai {name}: {n_species} spesies cocok dalam selisih 0,5%."
    return f"Reported as {name}: {n_species} species matched within 0.5%."


def unknown_reason(lang: str) -> str:
    if lang == "id":
        return "Tidak ada referensi yang cukup mirip; kemungkinan spesies belum ada di kamus."
    return "No sufficiently similar reference; the species may be missing from the reference."


def l1_reason(pid: float | None, species: str, gap: float | None, lang: str) -> str:
    if pid is None:
        return "Tidak ada kecocokan di referensi." if lang == "id" else "No match in the reference."
    if lang == "id":
        return f"Kemiripan {pct(pid)}% dengan {species}; selisih {pct(gap)}% dari spesies lain terdekat."
    return f"{pct(pid, 'en')}% identity to {species}; {pct(gap, 'en')}% from the nearest other species."


def completeness_reason(n_missing: int, n: int, genus: str, area: str, lang: str) -> str:
    if lang == "id":
        return f"{n_missing} dari {n} spesies {genus} di {area} belum punya referensi."
    return f"{n_missing} of {n} {genus} species in {area} lack a reference."


def l4_reason(k: int, r: int, control: str, lang: str) -> str:
    if lang == "id":
        return f"Positif di {k} dari {r} replikat; {control}."
    return f"Detected in {k} of {r} replicates; {control}."


def l2_reason(recorded: bool, area: str, via: str, lang: str) -> str:
    alias = ""
    if via.startswith("alias"):
        alias = f" (lewat alias {via.split(': ', 1)[1]})" if lang == "id" else f" (via alias {via.split(': ', 1)[1]})"
    if lang == "id":
        return f"{'Tercatat' if recorded else 'Tidak tercatat'} di checklist {area}{alias}."
    return f"{'Recorded' if recorded else 'Not recorded'} in the {area} checklist{alias}."


CONTROL_TEXT = {
    "bersih": ("kontrol negatif batch bersih", "negative controls of the batch are clean"),
    "terkontaminasi": ("DNA ini muncul di kontrol negatif batch yang sama", "this DNA appears in a negative control of the same batch"),
    "tanpa_kontrol": ("batch tanpa kontrol negatif", "batch has no negative control"),
}


def control_text(state: str, batches: str, lang: str) -> str:
    id_text, en_text = CONTROL_TEXT[state]
    text = id_text if lang == "id" else en_text
    return f"{text} ({batches})" if batches else text
