"""F20-F21: keputusan per klaim beserta tindak lanjut, dan kemungkinan asal-usul."""

from __future__ import annotations

import pandas as pd

from .taxonomy import same_species_name

UNKNOWN_TEXT = "ikan tidak dikenal, kemungkinan belum ada di kamus"


def decide(row: dict, rules: dict) -> tuple[str, str]:
    d = rules["decision"]
    labels = [x for x in str(row.get("label_L3", "")).split("; ") if x]
    has_l3 = any(lbl in d["l3_trigger_labels"] for lbl in labels)
    causes = row["penyebab"]
    if row["tingkat"] == "tidak dikenal":
        problem = "sampel" in causes
        decision = d["unknown"]["lab_signal_problem" if problem else "default"]
    else:
        decision = d["matrix"][row["nilai"]]["dengan_l3" if has_l3 else "tanpa_l3"]

    steps = [d["follow_up"][decision]]
    if decision != "aman dilaporkan":
        steps += [d["cause_follow_up"][c] for c in causes if c in d["cause_follow_up"]]
    if row["tingkat"] == "tidak dikenal":
        steps.append(f"Tulis sebagai \"{UNKNOWN_TEXT}\".")
    if "invasif" in labels and row["nilai"] in ("C", "D"):
        steps.append("Jangan dijadikan dasar pemberantasan sebelum dicek.")
    if "endemik" in labels and row["nilai"] == "D":
        steps.append("Klaim endemik bernilai D tidak dibuang, agar tidak berujung kesimpulan \"tidak ada\" yang keliru.")
    seen, unique = set(), []
    for s in steps:
        if s not in seen:
            seen.add(s)
            unique.append(s)
    return decision, " ".join(unique)


def origin(row: dict, reference, facility: str = "") -> str:
    """Tiga kalimat dengan bahasa "kemungkinan"; tidak pernah menyebut populasi atau sungai asal."""
    if row["tingkat"] not in ("spesies", "genus"):
        return ""
    path = reference.pathway(row["taxon_dilaporkan"])
    if not path:
        return ""
    lake = row.get("danau") or reference.region
    cl = reference.checklist_for(row.get("danau") or None)
    names = [path["spesies"], row["taxon_dilaporkan"]]
    st = cl[cl["spesies"].map(lambda s: any(same_species_name(s, n) for n in names))]["status"]
    labels = str(row.get("label_L3", ""))
    if len(st):
        status = st.iloc[0]
        if "invasif" in labels:
            status += ", invasif"
    else:
        status = "di luar sebaran alami yang tercatat"
    fac = facility or path.get("fasilitas_sekitar", "")
    fac_text = f" Fasilitas di sekitar lokasi: {fac}." if fac and fac != "belum diisi pengguna" else ""
    return (f"Status di {lake}: kemungkinan {status}. "
            f"Jalur masuk yang tercatat: {path['jalur']}. "
            f"Kemungkinan sumber DNA selain ikan hidup: {path.get('sumber_dna_lain', '-')}.{fac_text}")


def apply_decisions(claims: pd.DataFrame, reference, rules: dict, facilities: dict[str, str]) -> pd.DataFrame:
    out = claims.copy()
    dec, follow, orig = [], [], []
    memo: dict[tuple, str] = {}
    for row in out.to_dict("records"):
        k, t = decide(row, rules)
        dec.append(k)
        follow.append(t)
        fac = facilities.get(row["site_id"], "")
        key = (row["taxon_dilaporkan"], row["tingkat"], row["danau"], row["label_L3"], fac)
        if key not in memo:
            memo[key] = origin(row, reference, fac)
        orig.append(memo[key])
    out["keputusan"] = dec
    out["tindak_lanjut"] = follow
    out["asal_usul"] = orig
    return out
