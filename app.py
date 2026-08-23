"""PartForge demo — Streamlit UI.

Upload a raw 6-col catalogue CSV -> live stage progress -> preview -> download
output.xlsx / output.csv / audit_report.xlsx. API key via env or Streamlit
secrets (GEMINI_API_KEY). Run: streamlit run app.py
"""
from __future__ import annotations

import os
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from partforge import attributes, classify, descriptions, emit, enrich, features  # noqa: E402
from partforge import identity, io_loader, llm, packaging  # noqa: E402
from main import process_row  # noqa: E402

st.set_page_config(page_title="PartForge", page_icon="⚙️", layout="wide")


def _load_secrets_env() -> None:
    llm.load_env()
    try:
        for k in ("GEMINI_API_KEY", "PARTFORGE_MODEL"):
            if k in st.secrets:
                os.environ.setdefault(k, str(st.secrets[k]))
    except Exception:
        pass


_load_secrets_env()

st.title("⚙️ PartForge — AI Product Content Enrichment")
st.caption("Raw catalogue rows → Unilog 252-column Delivery Format. "
           "Deterministic rules first; LLM fills only evidenced gaps; every "
           "low-confidence cell is flagged, never invented.")

with st.sidebar:
    st.header("Run settings")
    use_llm = st.checkbox("LLM enrichment (Gemini)", value=llm.available(),
                          disabled=not llm.available())
    if not llm.available():
        st.warning("No GEMINI_API_KEY found — deterministic-only mode.")
    workers = st.slider("Parallel workers", 1, 32, 16)
    limit = st.number_input("Row limit (0 = all)", 0, 5000, 50)
    st.markdown("---")
    st.markdown("**Pipeline**\n\nS0 cleanse → S1 identity vote → S2 classify → "
                "S3 attributes → S5 features → S4 descriptions → S6 assets → "
                "S7 packaging → S8 validate → S9 emit")

uploaded = st.file_uploader("Upload input CSV", type=["csv"])
run_clicked = st.button("🚀 Enrich", type="primary", disabled=uploaded is None)

if uploaded is not None:
    tmp_path = os.path.join(".cache", "_upload.csv")
    os.makedirs(".cache", exist_ok=True)
    with open(tmp_path, "wb") as fh:
        fh.write(uploaded.getbuffer())

if run_clicked and uploaded is not None:
    df = io_loader.load_input(tmp_path)
    rows = df.to_dict("records")
    if limit:
        rows = rows[: int(limit)]
    n = len(rows)

    s = st.progress(0.0, text="Starting…")
    stat = st.empty()
    outputs, audits = [], []
    t0 = __import__("time").time()

    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=int(workers)) as ex:
        futs = {ex.submit(process_row, i, rec, bool(use_llm)): i for i, rec in enumerate(rows)}
        for k, fut in enumerate(as_completed(futs), start=1):
            try:
                out, audit = fut.result()
                outputs.append((futs[fut], out, audit))
            except Exception as exc:
                st.warning(f"row {futs[fut]} failed: {exc}")
            s.progress(k / n, text=f"{k}/{n} rows enriched")
            rate = k / max(__import__("time").time() - t0, 1e-6)
            stat.metric("rows/s", f"{rate:.1f}")

    outputs.sort(key=lambda t: t[0])
    out_rows = [o for _, o, _ in outputs]
    audits = [a for _, _, a in outputs]
    paths = emit.write_outputs(out_rows, audits, "out/")

    st.success(f"Done — {n} rows in {__import__('time').time()-t0:.0f}s · "
               f"{sum(1 for a in audits if a['flag'])} flagged NEEDS_REVIEW")

    left, right = st.columns([3, 1])
    with left:
        st.subheader("Preview")
        show = [c for c in ["Mfg_Part_Num", "MANUFACTURER_NAME", "BRAND_NAME",
                            "Classpath", "INVOICE_DESC", "MOBILE_DESC",
                            "ATTRIBUTE_LABEL 1", "ATTRIBUTE_VALUE 1",
                            "Actual Image (Yes/No)"] if c in out_rows[0]]
        st.dataframe(pd.DataFrame(out_rows)[show], use_container_width=True,
                     height=400)
    with right:
        st.subheader("Downloads")
        with open(paths["xlsx"], "rb") as fh:
            st.download_button("⬇️ output.xlsx", fh, "output.xlsx")
        with open(paths["csv"], "rb") as fh:
            st.download_button("⬇️ output.csv", fh, "output.csv", "text/csv")
        with open(paths["audit"], "rb") as fh:
            st.download_button("⬇️ audit_report.xlsx", fh, "audit_report.xlsx")

st.markdown("---")
st.caption("Honesty by design: blanks beat invented values — flagged cells carry "
           "reason codes in audit_report.xlsx (R-HON-01).")
