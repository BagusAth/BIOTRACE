"""F12-F15: audit per klaim (ASV x lokasi) pada empat lapisan bukti.

L4 sinyal lab, L1 kamus DNA, L2 kewajaran lokasi (skor), L3 status (label, tidak mengubah skor).
"""

from __future__ import annotations

import pandas as pd

from . import texts
from .io import CONTROL_TYPES
from .naming import Naming


def site_info(project) -> pd.DataFrame:
    """Satu baris per lokasi sampel: danau, batch, jumlah replikat, fasilitas sekitar."""
    s = project.samples.copy()
    s["rep_key"] = s["replicate"].where(s["replicate"].astype(str).str.strip() != "", s["sample_id"])
    rows = []
    for site, grp in s.groupby("site_id", sort=True):
        lakes = [x for x in grp["lake"] if x]
        fac = [x for x in grp.get("fasilitas_sekitar", pd.Series(dtype=str)) if x]
        rows.append({
            "site_id": site,
            "lake": lakes[0] if lakes else "",
            "batches": sorted({b for b in grp["extraction_batch"] if b}),
            "n_replikat": grp["rep_key"].nunique(),
            "fasilitas_sekitar": fac[0] if fac else "",
        })
    return pd.DataFrame(rows, columns=["site_id", "lake", "batches", "n_replikat", "fasilitas_sekitar"])


def audit_l4(project, rules: dict) -> pd.DataFrame:
    """F12: replikat positif per lokasi, data nyasar, kontrol negatif batch yang sama."""
    l4 = rules["l4"]
    meta = project.metadata[["sample_id", "site_id", "sample_type", "replicate", "extraction_batch"]]
    reads = project.reads.merge(meta, on="sample_id", how="left").fillna("")
    max_reads = reads.groupby("asv_id")["reads"].max()
    threshold = (max_reads * float(l4["tag_jump_fraction"])).to_dict()
    sites = site_info(project).set_index("site_id")
    controls = reads[reads["sample_type"].isin(CONTROL_TYPES)]
    control_batches = set(project.metadata.loc[project.metadata["sample_type"].isin(CONTROL_TYPES),
                                               "extraction_batch"])
    samples = reads[reads["sample_type"] == "sampel"].copy()
    samples["rep_key"] = samples["replicate"].where(samples["replicate"] != "", samples["sample_id"])
    samples["thr"] = samples["asv_id"].map(threshold).astype(float).fillna(0.0)
    samples["kept"] = samples["reads"] >= samples["thr"]

    grouped = samples.groupby(["asv_id", "site_id"], sort=True)
    agg = pd.DataFrame({
        "total": grouped["reads"].sum(),
        "n_rows": grouped["reads"].size(),
        "n_kept": grouped["kept"].sum(),
        "rep_seen": grouped["rep_key"].nunique(),
    })
    agg["k"] = samples[samples["kept"]].groupby(["asv_id", "site_id"])["rep_key"].nunique()
    agg["k"] = agg["k"].fillna(0).astype(int)

    # kontrol negatif yang memuat ASV di atas ambang data nyasar, per (asv, batch)
    controls = controls.assign(thr=controls["asv_id"].map(threshold).astype(float).fillna(0.0))
    hot = controls[controls["reads"] >= controls["thr"]]
    hot_batches: dict[str, set[str]] = {}
    for asv, batch in zip(hot["asv_id"], hot["extraction_batch"]):
        hot_batches.setdefault(asv, set()).add(batch)

    rows = []
    for (asv, site), a in agg.iterrows():
        k = int(a["k"])
        info = sites.loc[site] if site in sites.index else None
        r = int(info["n_replikat"]) if info is not None else int(a["rep_seen"])
        batches = list(info["batches"]) if info is not None else []
        total = int(a["total"])

        hot_here = sorted(hot_batches.get(asv, set()) & set(batches))
        with_ctrl = [b for b in batches if b in control_batches]
        if hot_here:
            state, cb = "terkontaminasi", ", ".join(hot_here)
        elif with_ctrl:
            state, cb = "bersih", ", ".join(with_ctrl)
        else:
            state, cb = "tanpa_kontrol", ", ".join(batches)

        caps = []
        if state == "terkontaminasi":
            caps.append(f"DNA muncul di kontrol negatif batch yang sama ({cb})")
        if total < int(l4["min_total_reads"]):
            caps.append(f"semua bacaan di bawah {l4['min_total_reads']} (total {total})")
        score = int(l4["score_by_positive"].get(min(k, int(l4["replicates"])), 0))
        rows.append({
            "asv_id": asv, "site_id": site, "replikat_positif": k, "replikat_total": r,
            "total_bacaan": total, "bacaan_nyasar_dibuang": int(a["n_rows"] - a["n_kept"]),
            "status_kontrol": state, "batch_kontrol": cb, "batas_D": "; ".join(caps),
            "skor_L4": score,
            "alasan_L4_id": texts.l4_reason(k, r, texts.control_text(state, cb, "id"), "id"),
            "alasan_L4_en": texts.l4_reason(k, r, texts.control_text(state, cb, "en"), "en"),
        })
    return pd.DataFrame(rows)


def score_l1(n: Naming, comp: dict | None, rules: dict) -> dict:
    """F13: kemiripan, selisih dengan spesies lain terdekat, dan kelengkapan kamus."""
    l1 = rules["l1"]
    raw = 0
    if n.rank != "tidak dikenal" and n.best_identity is not None:
        gap = n.gap if n.gap is not None else 0.0
        if n.best_identity >= l1["score2"]["identity"] and gap >= l1["score2"]["gap"]:
            raw = 2
        elif n.best_identity >= l1["score1"]["identity"] and gap >= l1["score1"]["gap"]:
            raw = 1
    penalty = 0
    if raw and comp and comp["n"] > 0 and comp["r"] / comp["n"] < l1["completeness_penalty_below"]:
        penalty = 1
    score = max(0, raw - penalty)
    if n.rank == "tidak dikenal":
        rid, ren = texts.unknown_reason("id"), texts.unknown_reason("en")
    else:
        rid = texts.l1_reason(n.best_identity, n.best_species, n.gap, "id")
        ren = texts.l1_reason(n.best_identity, n.best_species, n.gap, "en")
    if comp:
        miss = comp["n"] - comp["r"]
        rid += " " + texts.completeness_reason(miss, comp["n"], comp["genus"], comp["wilayah"], "id")
        ren += " " + texts.completeness_reason(miss, comp["n"], comp["genus"], comp["wilayah"], "en")
    return {"skor_L1": score, "skor_L1_mentah": raw, "potongan_kelengkapan": penalty,
            "alasan_L1_id": rid, "alasan_L1_en": ren}


def score_l2(n: Naming, reference, lake: str, rules: dict) -> dict:
    """F14: tercatat di checklist perairan, termasuk lewat tabel alias."""
    area = lake or reference.region
    if n.rank == "tidak dikenal":
        return {"skor_L2": 0, "l2_dinilai": False,
                "alasan_L2_id": "Tidak dinilai: nama tidak dikenal.",
                "alasan_L2_en": "Not assessed: name unknown."}
    hit, via = reference.checklist_hit(n.taxon, n.rank, lake or None)
    score = rules["l2"]["score_recorded"] if hit else rules["l2"]["score_not_recorded"]
    return {"skor_L2": int(score), "l2_dinilai": True,
            "alasan_L2_id": texts.l2_reason(hit, area, via, "id"),
            "alasan_L2_en": texts.l2_reason(hit, area, via, "en")}


def audit_claims(project, namings: dict[str, Naming], reference, rules: dict) -> pd.DataFrame:
    """Gabungkan L4 per lokasi dengan L1, L2, L3 dari penamaan menjadi satu baris per klaim."""
    l4 = audit_l4(project, rules)
    sites = site_info(project).set_index("site_id")
    lake_of = sites["lake"].to_dict()
    scope = rules["reference"].get("completeness_scope", "wilayah")
    # takson x danau jauh lebih sedikit daripada klaim: hitung sekali per pasangan
    memo: dict[tuple, tuple] = {}
    rows = []
    for rec in l4.to_dict("records"):
        n = namings[rec["asv_id"]]
        lake = lake_of.get(rec["site_id"], "")
        key = (rec["asv_id"], lake)
        if key not in memo:
            comp = reference.completeness_for(n.genus, lake or None, scope) if n.genus else None
            memo[key] = (comp, score_l1(n, comp, rules), score_l2(n, reference, lake, rules),
                         reference.l3_labels(n.taxon, n.rank, lake or None, near_family=n.family_hint))
        comp, l1, l2, labels = memo[key]
        rows.append({
            "claim_id": f"{rec['asv_id']}@{rec['site_id']}",
            "asv_id": rec["asv_id"], "site_id": rec["site_id"], "danau": lake,
            "taxon_lab": n.taxon_lab, "taxon_dilaporkan": n.taxon, "tingkat": n.rank,
            "kecocokan_dalam_0,5%": "; ".join(n.near_species),
            "kemiripan_terbaik": n.best_identity, "selisih_spesies_lain": n.gap,
            "sumber_penamaan": n.source, "catatan_penamaan": "; ".join(n.notes),
            "penyebab_penamaan": n.causes,
            **{k: v for k, v in rec.items() if k not in ("asv_id", "site_id")},
            **l1, **l2,
            "label_L3": "; ".join(labels),
            "kelengkapan": comp,
        })
    return pd.DataFrame(rows)
