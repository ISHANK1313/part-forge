"""Merge LLM-enriched subset with deterministic remainder -> final deliverable.

v3: sources are out_det/ (pristine full-deterministic) + out_llm/ (LLM subset).
Positional record merge; row order preserved.
"""
import pandas as pd

det = pd.read_excel("out_det/output.xlsx", dtype=str).fillna("")
llm = pd.read_excel("out_llm/output.xlsx", dtype=str).fillna("")
MPN = "Mfg_Part_Num"
assert list(det.columns) == list(llm.columns), "header drift between runs"

llm_map: dict[str, dict] = {}
for rec in llm.to_dict("records"):
    llm_map.setdefault(rec[MPN], rec)

hits = 0
cols = list(det.columns)
out_rows: list[list[str]] = []
for rec in det.to_dict("records"):
    sub = llm_map.get(rec[MPN])
    src = sub if sub else rec
    out_rows.append([str(src.get(c, "") or "") for c in cols])
    hits += 1 if sub else 0
merged = pd.DataFrame(out_rows, columns=cols)
print(f"merged {hits} LLM rows over deterministic base -> {len(merged)} total")
assert (merged[MPN] == "").sum() == 0, "blank MPN after merge!"

with pd.ExcelWriter("out/output.xlsx", engine="openpyxl") as xw:
    merged.to_excel(xw, index=False, sheet_name="Output")
merged.to_csv("out/output.csv", index=False, encoding="utf-8-sig")

det_a = pd.read_excel("out_det/audit_report.xlsx", dtype=str).fillna("")
llm_a = pd.read_excel("out_llm/audit_report.xlsx", dtype=str).fillna("")
a_map = {rec["MPN"]: rec for rec in llm_a.to_dict("records")}
acols = list(det_a.columns)
arows: list[list[str]] = []
for rec in det_a.to_dict("records"):
    sub = a_map.get(rec["MPN"])
    src = sub if sub else rec
    arows.append([str(src.get(c, "") or "") for c in acols])
aud = pd.DataFrame(arows, columns=acols)
with pd.ExcelWriter("out/audit_report.xlsx", engine="openpyxl") as aw:
    aud.to_excel(aw, index=False, sheet_name="Row Audit")
print("audits merged")
