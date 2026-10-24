"""Antarmuka Streamlit BioTrace Indonesia (tahap 5).

    streamlit run app.py
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from biotrace import __version__
from biotrace.config import ROOT, load_rules
from biotrace.pipeline import DECISIONS, run
from biotrace.provenance import fingerprint
from biotrace.reference import load_reference
from biotrace.report import (CATEGORY_ACTION, OUTPUT_LABELS, SIM_LABEL, barcode_priority, build_pdf,
                             claims_csv, decision_summary, evidence_card, gap_map)

DEMO_DIR = ROOT / "data" / "demo" / "matano"
DEMO_FILES = {"reads": "bacaan.csv", "metadata": "metadata.csv", "taxonomy": "taksonomi.csv", "fasta": "asv.fasta"}
PAGES = ["1. Unggah", "2. Ringkasan keputusan", "3. Tabel klaim", "4. Evidence Card", "5. Peta celah"]

st.set_page_config(page_title="BioTrace Indonesia", layout="wide")


class NamedBytes(io.BytesIO):
    def __init__(self, data: bytes, name: str):
        super().__init__(data)
        self.name = name


@st.cache_resource
def resources():
    return load_rules(), load_reference()


def italic(name: str) -> str:
    return f"*{name}*" if name and name[0].isupper() else name


def run_project(files: dict[str, NamedBytes | None], simulation: bool) -> None:
    rules, ref = resources()
    report = run(files["reads"], files["metadata"], files.get("taxonomy"), files.get("fasta"),
                 rules=rules, reference=ref, simulation=simulation)
    st.session_state["report"] = report
    st.rerun()   # judul, label SIMULASI, dan tombol ekspor ikut diperbarui


def page_upload() -> None:
    st.header("Unggah data lab")
    st.caption("Tiga CSV (tabel bacaan, metadata, taksonomi) dan FASTA urutan ASV. "
               "FASTA dianjurkan: memicu pencocokan ulang ke referensi tervalidasi.")
    c1, c2 = st.columns(2)
    reads = c1.file_uploader("Tabel bacaan (wajib)", type=["csv", "tsv", "txt"])
    meta = c1.file_uploader("Metadata sampel (wajib)", type=["csv", "tsv", "txt"])
    tax = c2.file_uploader("Taksonomi lab (wajib bila tanpa FASTA)", type=["csv", "tsv", "txt"])
    fasta = c2.file_uploader("Urutan ASV FASTA (dianjurkan)", type=["fasta", "fa", "fna", "txt"])
    b1, b2 = st.columns(2)
    if b1.button("Periksa data", type="primary", disabled=not (reads and meta)):
        files = {"reads": NamedBytes(reads.getvalue(), reads.name), "metadata": NamedBytes(meta.getvalue(), meta.name),
                 "taxonomy": NamedBytes(tax.getvalue(), tax.name) if tax else None,
                 "fasta": NamedBytes(fasta.getvalue(), fasta.name) if fasta else None}
        with st.spinner("Mencocokkan ke referensi dan mengaudit klaim..."):
            run_project(files, simulation=False)
    demo_ok = all((DEMO_DIR / f).exists() for f in DEMO_FILES.values())
    if b2.button(f"Muat demo Danau Matano ({SIM_LABEL})", disabled=not demo_ok):
        files = {k: NamedBytes((DEMO_DIR / f).read_bytes(), f) for k, f in DEMO_FILES.items()}
        with st.spinner("Menjalankan skenario demo..."):
            run_project(files, simulation=True)

    report = st.session_state.get("report")
    if not report:
        return
    st.success(f"Selesai dalam {report.seconds:.1f} detik. {report.summary_sentence()}")
    st.subheader("Informasi yang hilang")
    if report.project.missing_info:
        for m in report.project.missing_info:
            st.markdown(f"- {m}")
    else:
        st.markdown("Tidak ada.")
    st.subheader("Sidik jari tiap berkas")
    st.dataframe(pd.DataFrame([{"berkas": f.name, "peran": f.role, "sha256": f.sha256} for f in report.project.files]),
                 hide_index=True, width="stretch")
    st.code(f"sidik jari laporan: sha256:{report.fingerprint}\nreferensi: {report.manifest['referensi']}\n"
            f"aturan: {report.manifest['aturan']}\naplikasi: {report.manifest['aplikasi']}")


def page_summary(report) -> None:
    summ = decision_summary(report)
    st.header("Ringkasan keputusan")
    st.markdown(f"### {summ['kalimat']}")
    cols = st.columns(len(DECISIONS) + 1)
    for col, d in zip(cols, DECISIONS):
        col.metric(d, summ["jumlah"][d])
    cols[-1].metric("tidak dikenal", summ["jumlah"]["tidak dikenal"])
    st.subheader("Tindak lanjut per kategori")
    for d in DECISIONS:
        if summ["jumlah"][d]:
            st.markdown(f"**{d}** ({summ['jumlah'][d]}): {CATEGORY_ACTION[d]}")
    st.warning(summ["batas_interpretasi"])


def page_claims(report) -> None:
    st.header("Tabel klaim")
    c = report.claims
    f1, f2 = st.columns(2)
    dec = f1.multiselect("Keputusan", DECISIONS, default=list(DECISIONS))
    causes = f2.multiselect("Penyebab", ["referensi", "marker", "sampel", "lokasi"])
    view = c[c["keputusan"].isin(dec)]
    if causes:
        view = view[view["penyebab"].map(lambda s: any(x in s.split("; ") for x in causes))]
    cols = ["claim_id", "site_id", "danau", "taxon_lab", "taxon_dilaporkan", "tingkat", "nilai", "total",
            "label_L3", "peluang_belum_di_kamus", "penyebab", "keputusan"]
    st.caption(f"{len(view)} dari {len(c)} klaim")
    st.dataframe(view[cols], hide_index=True, width="stretch")


def page_card(report) -> None:
    st.header(f"{SIM_LABEL} — Evidence Card" if report.simulation else "Evidence Card")
    c = report.claims
    claim_id = st.selectbox("Klaim", c["claim_id"].tolist(),
                            format_func=lambda x: f"{x} · {c.set_index('claim_id').loc[x, 'taxon_dilaporkan']}")
    card = evidence_card(c[c["claim_id"] == claim_id].iloc[0].to_dict(), report)
    if card["simulasi"]:
        st.error(f"{SIM_LABEL}: data demo sintetis, bukan hasil lapangan.")
    st.subheader(f"{italic(card['nama'])} · {card['lokasi']}")
    st.caption(f"Nama dari lab/kecocokan terbaik: {italic(card['taxon_lab']) or '-'}")
    o1, o2, o3, o4 = st.columns(4)
    o1.metric(OUTPUT_LABELS["tingkat"][0], card["tingkat"])
    o2.metric(OUTPUT_LABELS["nilai"][0], f"{card['nilai']} ({card['total']}/5)")
    o3.metric(OUTPUT_LABELS["peluang"][0], card["peluang"])
    o4.metric(OUTPUT_LABELS["penyebab"][0], card["penyebab"])
    st.markdown(f"**Keputusan: {card['keputusan']}** · Label L3: {card['label_L3']} · Galat nilai: {card['galat']}")
    if card["batas"]:
        st.markdown(f"Batas D diterapkan: {card['batas']}")
    st.table(pd.DataFrame(card["alasan"], columns=["Lapisan", "Bahasa Indonesia", "English"]))
    st.markdown(f"**Tindak lanjut:** {card['tindak_lanjut']}")
    if card["asal_usul"]:
        st.markdown(f"**Kemungkinan asal-usul:** {card['asal_usul']}")
    st.info(f"{card['batas_interpretasi'][0]} / {card['batas_interpretasi'][1]}")


def page_gaps(report) -> None:
    st.header("Peta celah kamus")
    st.dataframe(gap_map(report), hide_index=True, width="stretch")
    st.subheader("Daftar prioritas barcode")
    st.dataframe(barcode_priority(report), hide_index=True, width="stretch")


def sidebar_downloads(report) -> None:
    st.sidebar.subheader("Ekspor")
    prefix = "SIMULASI_" if report.simulation else ""
    st.sidebar.download_button("Laporan PDF", build_pdf(report), f"{prefix}laporan_biotrace.pdf", "application/pdf")
    st.sidebar.download_button("Tabel klaim CSV", claims_csv(report), f"{prefix}klaim.csv", "text/csv")
    st.sidebar.download_button("Prioritas barcode CSV",
                               barcode_priority(report).to_csv(index=False).encode("utf-8"),
                               f"{prefix}prioritas_barcode.csv", "text/csv")
    doc = dict(report.manifest, sidik_jari_laporan=f"sha256:{fingerprint(report.manifest, report.claims)}")
    st.sidebar.download_button("Manifest JSON", json.dumps(doc, indent=2, ensure_ascii=False).encode("utf-8"),
                               f"{prefix}manifest.json", "application/json")


def main() -> None:
    report = st.session_state.get("report")
    title = "BioTrace Indonesia"
    if report and report.simulation:
        title = f"{SIM_LABEL} — {title}"
    st.title(title)
    st.caption(f"Biodiversitas Indonesia, dibaca dengan data Indonesia · biotrace {__version__}")
    page = st.sidebar.radio("Halaman", PAGES)
    if report:
        sidebar_downloads(report)
    if page == PAGES[0]:
        page_upload()
        return
    if not report:
        st.info("Unggah data atau muat demo di halaman 1 terlebih dahulu.")
        return
    {PAGES[1]: page_summary, PAGES[2]: page_claims, PAGES[3]: page_card, PAGES[4]: page_gaps}[page](report)


main()
