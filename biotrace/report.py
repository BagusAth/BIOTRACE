"""F22-F25: ringkasan keputusan, Evidence Card, ekspor PDF dan CSV, daftar prioritas barcode."""

from __future__ import annotations

import datetime as dt
import io
import json
import re
from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd

from .pipeline import DECISIONS, Report
from .provenance import write_manifest
from .taxonomy import genus_of, species_key
from .texts import frac

SIM_LABEL = "SIMULASI"
CATEGORY_ACTION = {
    "aman dilaporkan": "Masukkan ke laporan pada tingkat nama yang tercantum.",
    "dengan catatan": "Tulis di tingkat yang aman (genus atau tidak dikenal) dan cek kemungkinan sumber DNA lain.",
    "wajib verifikasi": "Jadwalkan verifikasi: marker kedua (COI/16S), survei tangkap, atau barcode spesimen voucher.",
    "jangan dipakai": "Keluarkan dari laporan; tinjau batch ekstraksi dan ulang PCR bila perlu.",
}
OUTPUT_LABELS = {
    "tingkat": ("Tingkat nama yang aman", "Safe name level"),
    "nilai": ("Nilai bukti", "Evidence grade"),
    "peluang": ("Peluang spesies asli belum di kamus", "Chance the true species is missing from the reference"),
    "penyebab": ("Penyebab ketidakpastian", "Cause of uncertainty"),
}


# ---- ringkasan dan kartu ----------------------------------------------------------------
def decision_summary(report: Report) -> dict:
    s = report.summary
    actions = {d: CATEGORY_ACTION[d] for d in DECISIONS if s[d] > 0}
    return {"kalimat": report.summary_sentence(), "jumlah": s, "tindak_lanjut": actions,
            "batas_interpretasi": report.rules["interpretation_limit"]["id"]}


def evidence_card(row: dict, report: Report) -> dict:
    p = row["peluang_belum_di_kamus"]
    p_text = "tidak dihitung" if p is None or pd.isna(p) else frac(float(p))
    name = row["taxon_dilaporkan"] if row["tingkat"] != "tidak dikenal" else "tidak dikenal"
    return {
        "judul": f"{SIM_LABEL} — " if report.simulation else "",
        "claim_id": row["claim_id"],
        "lokasi": f"{row['site_id']} ({row['danau'] or report.reference.region})",
        "nama": name,
        "tingkat": row["tingkat"],
        "taxon_lab": row["taxon_lab"],
        "nilai": row["nilai"],
        "total": row["total"],
        "galat": row["galat_nilai"],
        "batas": row["batas_diterapkan"],
        "peluang": p_text,
        "penyebab": row["penyebab"] or "-",
        "label_L3": row["label_L3"] or "-",
        "keputusan": row["keputusan"],
        "tindak_lanjut": row["tindak_lanjut"],
        "asal_usul": row["asal_usul"],
        "alasan": [
            ("Penamaan", row["alasan_penamaan_id"], row["alasan_penamaan_en"]),
            (f"L1 kamus DNA ({row['skor_L1']}/2)", row["alasan_L1_id"], row["alasan_L1_en"]),
            (f"L2 lokasi ({row['skor_L2']}/1)", row["alasan_L2_id"], row["alasan_L2_en"]),
            (f"L4 sinyal lab ({row['skor_L4']}/2)", row["alasan_L4_id"], row["alasan_L4_en"]),
        ],
        "batas_interpretasi": (report.rules["interpretation_limit"]["id"], report.rules["interpretation_limit"]["en"]),
        "simulasi": report.simulation,
    }


def cards_for_pdf(report: Report) -> pd.DataFrame:
    c = report.claims
    return c[c["nilai"].isin(["B", "C", "D"]) | (c["tingkat"] == "tidak dikenal")]


# ---- daftar prioritas barcode (F25) ----------------------------------------------------------
def barcode_priority(report: Report) -> pd.DataFrame:
    """Target sekuensing dari klaim tidak dikenal dan celah kamus, terdampak terbanyak di atas."""
    c = report.claims
    ref = report.reference
    rows = []
    unknown = c[c["tingkat"] == "tidak dikenal"]
    for asv, grp in unknown.groupby("asv_id", sort=True):
        near = grp["taxon_lab"].iloc[0]
        pid = grp["kemiripan_terbaik"].iloc[0]
        hint = f"terdekat {near} {pid:.1f}%" if near and pid is not None and not pd.isna(pid) else "tanpa kecocokan"
        rows.append({"target": f"ASV {asv} (tidak dikenal; {hint})", "jenis": "tidak dikenal",
                     "danau": "; ".join(sorted({d for d in grp["danau"] if d})) or ref.region,
                     "jumlah_klaim_terdampak": len(grp), "status_L3": grp["label_L3"].iloc[0],
                     "alasan": "tidak ada referensi yang cukup mirip"})

    ref_claims = c[(c["tingkat"].isin(["genus", "famili"])) & c["penyebab"].str.contains("referensi")]
    lakes = sorted({d for d in c["danau"] if d}) or [None]
    for lake in lakes:
        cl = ref.checklist_for(lake)
        here = ref_claims if lake is None else ref_claims[ref_claims["danau"] == lake]
        validated = set(ref.taxonomy.loc[ref.taxonomy["status_validasi"] == "tervalidasi", "spesies_kunci"])
        for sp in sorted({s for s in cl["spesies"] if species_key(s)[1]}):
            if species_key(sp)[0] in validated:
                continue
            affected = here[here["taxon_dilaporkan"] == genus_of(sp)]
            labels = ref.l3_labels(sp, "spesies", lake)
            rows.append({"target": sp, "jenis": "celah kamus", "danau": lake or ref.region,
                         "jumlah_klaim_terdampak": len(affected), "status_L3": "; ".join(labels),
                         "alasan": "belum punya sekuens 12S tervalidasi"})
        # spesies terdekat yang ada di referensi tetapi belum tervalidasi
        for taxon_lab, grp in here[here["taxon_dilaporkan"] != ""].groupby("taxon_lab", sort=True):
            key, resolved = species_key(taxon_lab)
            if not resolved or key in validated or any(r["target"] == key for r in rows):
                continue
            rows.append({"target": key, "jenis": "sekuens belum tervalidasi", "danau": lake or ref.region,
                         "jumlah_klaim_terdampak": len(grp), "status_L3": "; ".join(ref.l3_labels(key, "spesies", lake)),
                         "alasan": "sekuens ada tetapi tanpa specimen_voucher"})
    df = pd.DataFrame(rows, columns=["target", "jenis", "danau", "jumlah_klaim_terdampak", "status_L3", "alasan"])
    if df.empty:
        return df
    df["_endemik"] = df["status_L3"].str.contains("endemik").astype(int)
    df = df.sort_values(["jumlah_klaim_terdampak", "_endemik", "target"], ascending=[False, False, True])
    return df.drop(columns="_endemik").reset_index(drop=True)


def gap_map(report: Report) -> pd.DataFrame:
    """Kelengkapan per genus untuk danau proyek dan wilayah."""
    ref = report.reference
    areas = sorted({d for d in report.claims["danau"] if d}) + [ref.region]
    comp = ref.completeness[ref.completeness["wilayah"].isin(areas)].copy()
    return comp.sort_values(["wilayah", "p_belum_di_kamus", "genus"], ascending=[True, False, True]).reset_index(drop=True)


# ---- PDF Bahasa Indonesia (F24) ------------------------------------------------------------
def _italicize(text: str, names: list[str]) -> str:
    """Escape untuk Paragraph reportlab lalu miringkan nama ilmiah."""
    out = escape(str(text))
    for n in sorted({x for x in names if x and x[0].isupper()}, key=len, reverse=True):
        out = re.sub(rf"(?<![\w>]){re.escape(escape(n))}(?![\w<])", f"<i>{escape(n)}</i>", out)
    return out


def build_pdf(report: Report, max_cards: int = 300) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                    TableStyle)

    styles = getSampleStyleSheet()
    h1, h2, body = styles["Title"], styles["Heading2"], styles["BodyText"]
    small = ParagraphStyle("small", parent=body, fontSize=8, leading=10)
    warn = ParagraphStyle("warn", parent=body, textColor=colors.HexColor("#8a1c1c"), fontName="Helvetica-Bold")
    names = set(report.claims["taxon_dilaporkan"]) | set(report.claims["taxon_lab"]) | set(report.reference.checklist["spesies"])
    names = sorted(names | {genus_of(n) for n in names})
    it = lambda t: _italicize(t, names)  # noqa: E731

    summ = decision_summary(report)
    sim = f"{SIM_LABEL} — " if report.simulation else ""
    story = [Paragraph(f"{sim}Laporan BioTrace Indonesia", h1)]
    if report.simulation:
        story.append(Paragraph("Data demo sintetis berlabel SIMULASI; bukan hasil lapangan.", warn))
    story += [Paragraph("Ringkasan keputusan", h2), Paragraph(summ["kalimat"], body), Spacer(1, 6)]
    rows = [["Keputusan", "Jumlah klaim", "Tindak lanjut"]]
    for d in DECISIONS:
        rows.append([d, str(summ["jumlah"][d]), Paragraph(CATEGORY_ACTION[d], small)])
    t = Table(rows, colWidths=[3.5 * cm, 2.5 * cm, 11 * cm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                           ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef3")),
                           ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story += [t, Spacer(1, 8), Paragraph(f"<b>{escape(summ['batas_interpretasi'])}</b>", body), Spacer(1, 6)]
    if report.project.missing_info:
        story.append(Paragraph("Informasi yang hilang", h2))
        for m in report.project.missing_info:
            story.append(Paragraph(f"• {escape(m)}", small))
    story.append(Paragraph(f"Sidik jari laporan: sha256:{report.fingerprint}", small))

    cards = cards_for_pdf(report)
    story += [PageBreak(), Paragraph(f"{sim}Evidence Card (nilai B–D dan tidak dikenal)", h2)]
    for row in cards.head(max_cards).to_dict("records"):
        card = evidence_card(row, report)
        head = (f"{sim}<b>{escape(card['claim_id'])}</b> · {escape(card['lokasi'])} · "
                f"{it(card['nama'])} ({escape(card['tingkat'])}) · nilai {card['nilai']} · "
                f"<b>{escape(card['keputusan'])}</b>")
        grid = [
            [Paragraph(OUTPUT_LABELS["tingkat"][0], small), Paragraph(f"{it(card['nama'])} ({escape(card['tingkat'])})", small)],
            [Paragraph(OUTPUT_LABELS["nilai"][0], small), Paragraph(f"{card['nilai']} (skor {card['total']}/5; galat: {escape(card['galat'])})"
                                                                 + (f"; batas D: {escape(card['batas'])}" if card["batas"] else ""), small)],
            [Paragraph(OUTPUT_LABELS["peluang"][0], small), Paragraph(escape(card["peluang"]), small)],
            [Paragraph(OUTPUT_LABELS["penyebab"][0], small), Paragraph(escape(card["penyebab"]), small)],
            [Paragraph("Label L3", small), Paragraph(escape(card["label_L3"]), small)],
        ]
        for layer, rid, ren in card["alasan"]:
            grid.append([Paragraph(escape(layer), small), Paragraph(f"{it(rid)}<br/><font color='#555555'>{it(ren)}</font>", small)])
        grid.append([Paragraph("Tindak lanjut", small), Paragraph(it(card["tindak_lanjut"]), small)])
        if card["asal_usul"]:
            grid.append([Paragraph("Kemungkinan asal-usul", small), Paragraph(it(card["asal_usul"]), small)])
        grid.append([Paragraph("Batas interpretasi", small), Paragraph(escape(card["batas_interpretasi"][0]), small)])
        tbl = Table(grid, colWidths=[4.5 * cm, 12.5 * cm])
        tbl.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story.append(KeepTogether([Paragraph(head, body), tbl, Spacer(1, 10)]))
    if len(cards) > max_cards:
        story.append(Paragraph(f"{len(cards) - max_cards} kartu lain ada di CSV klaim.", small))

    prio = barcode_priority(report)
    story += [PageBreak(), Paragraph("Daftar prioritas barcode", h2)]
    if prio.empty:
        story.append(Paragraph("Tidak ada target.", body))
    else:
        rows = [["Target", "Danau", "Klaim", "Status L3"]]
        for r in prio.head(60).to_dict("records"):
            rows.append([Paragraph(it(r["target"]), small), Paragraph(escape(r["danau"]), small),
                         str(r["jumlah_klaim_terdampak"]), Paragraph(escape(r["status_L3"] or "-"), small)])
        t = Table(rows, colWidths=[8 * cm, 3 * cm, 1.5 * cm, 4.5 * cm])
        t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
                               ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef3"))]))
        story.append(t)

    story += [PageBreak(), Paragraph("Lampiran: manifest dan versi", h2)]
    m = report.manifest
    story.append(Paragraph(f"Sidik jari laporan: sha256:{report.fingerprint}", small))
    for k in ("aplikasi", "referensi", "aturan", "mode"):
        if k in m:
            story.append(Paragraph(f"<b>{k}</b>: {escape(str(m[k]))}", small))
    story.append(Paragraph("<b>input</b>:", small))
    for name, digest in m["input"].items():
        story.append(Paragraph(f"• {escape(name)}: {digest}", small))
    story.append(Paragraph("<b>tabel acuan</b>:", small))
    for name, digest in m.get("tabel_acuan", {}).items():
        story.append(Paragraph(f"• {escape(name)}: {digest}", small))
    story.append(Paragraph("Sitasi data: mitohelper (Lim & Thompson 2021), NCBI GenBank, MitoFish, GBIF, IUCN Red List, "
                           "Kottelat 1990-1991, Herder dkk. 2006, Hedianto & Sentosa 2019.", small))

    buf = io.BytesIO()

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        text = f"{'SIMULASI · ' if report.simulation else ''}{report.rules['interpretation_limit']['id']} · halaman {doc.page}"
        canvas.drawString(2 * cm, 1.2 * cm, text)
        canvas.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm,
                            bottomMargin=1.8 * cm, title=f"{sim}Laporan BioTrace", author="BioTrace Indonesia",
                            invariant=1)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()


# ---- tulis semua keluaran ------------------------------------------------------------------
def claims_csv(report: Report) -> bytes:
    return report.claims.to_csv(index=False, lineterminator="\n").encode("utf-8")


def write_outputs(report: Report, out_dir: str | Path) -> dict[str, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "klaim": out / "klaim.csv",
        "prioritas_barcode": out / "prioritas_barcode.csv",
        "laporan": out / "laporan.pdf",
        "manifest": out / "manifest.json",
        "ringkasan": out / "ringkasan.json",
    }
    paths["klaim"].write_bytes(claims_csv(report))
    barcode_priority(report).to_csv(paths["prioritas_barcode"], index=False, lineterminator="\n")
    paths["laporan"].write_bytes(build_pdf(report))
    stamp = dt.datetime.now().isoformat(timespec="seconds")
    write_manifest(paths["manifest"], report.manifest, report.claims, run_time=f"{stamp} ({report.seconds:.1f} dtk)")
    summ = decision_summary(report)
    summ["waktu_proses_detik"] = round(report.seconds, 2)
    summ["sidik_jari_laporan"] = f"sha256:{report.fingerprint}"
    paths["ringkasan"].write_text(json.dumps(summ, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return paths
