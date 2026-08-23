"""S9 — Emission: assemble working rows into the exact 252-col Delivery Format.

Header order is authoritative from reference/expected_headers.csv. Never rename,
reorder, or drop headers (R-HON-03). Writes output.xlsx + output.csv +
audit_report.xlsx. Passthrough columns are copied verbatim (gold shows
placeholders preserved).
"""
from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from .assets import actual_image_flag, mfr_url, name_assets, ref_urls
from .features import product_title
from .validate import load_expected_headers

PASSTHROUGH_INPUT = ["Mfg_Part_Num", "Part_Desc", "E1_Brand", "Unilog_Brand",
                     "DIB_Brand", "Part_Manuf"]


def assemble_row(row: dict) -> dict:
    """Map one enriched working row onto the 252 output headers."""
    out: dict = {h: "" for h in load_expected_headers()}

    # -- URLs (constructed patterns, manufacturer-owned domains only) --------
    domain = row.get("domain") or ""
    mpn = (row.get("Mfg_Part_Num") or "").strip()
    out["MFR URL"] = mfr_url(domain, mpn)
    for i, u in enumerate(ref_urls(domain)[:5], start=1):
        out[f"Ref URL {i}"] = u

    # PART_NUMBER / Dept / Class / Fine / SKU - MY_PART_NUMBER: internal Unilog
    # ids, not derivable from input -> stay blank by design (R-HON-01).

    # -- Passthrough verbatim -------------------------------------------------
    for col in PASSTHROUGH_INPUT:
        out[col] = row.get(col) or ""

    # -- Identity -------------------------------------------------------------
    out["MANUFACTURER_NAME"] = row.get("manufacturer_name") or ""
    out["BRAND_NAME"] = row.get("brand_name") or ""
    out["TRADE_NAME"] = ""                       # R-ID-06
    out["MANUFACTURER_PART_NUMBER"] = mpn

    out["Classpath"] = row.get("classpath") or ""

    # -- Descriptions ----------------------------------------------------------
    for col in ("MOBILE_DESC", "INVOICE_DESC", "SHORT_DESC", "LONG_DESC1",
                "RETAIL_DESC", "MARKETING_DESCRIPTION"):
        out[col] = row.get(col) or ""

    # -- Features ---------------------------------------------------------------
    feats = row.get("features") or []
    for i in range(1, 21):
        if i <= len(feats):
            out[f"ITEM_FEATURES_{i}"] = str(feats[i - 1])

    wf = (row.get("with_feature") or "").strip()
    out["With"] = f"With {wf}" if wf else ""
    approvals = row.get("approvals") or []
    out["Standard/Approvals"] = "|".join(approvals)
    out["Application"] = row.get("application") or ""
    inc = row.get("includes")
    if isinstance(inc, list):
        inc = ", ".join(str(x) for x in inc)
    out["Includes"] = (inc or "").strip()
    out["Product Name"] = product_title(row.get("item_type") or "")

    # -- Attribute triplets (max 50) --------------------------------------------
    triplets = (row.get("_attributes") or [])[:50]
    for i in range(1, 51):
        if i <= len(triplets):
            t = triplets[i - 1]
            out[f"ATTRIBUTE_LABEL {i}"] = str(t.get("label", ""))
            out[f"ATTRIBUTE_VALUE {i}"] = str(t.get("value", ""))
            out[f"ATTRIBUTE_UOM {i}"] = str(t.get("uom", ""))

    # -- Commercial --------------------------------------------------------------
    pkg = row.get("_packaging") or {}
    out["Warranty"] = row.get("warranty") or ""
    out["Selling Qty"] = pkg.get("Selling Qty", "")
    out["Selling UOM"] = pkg.get("Selling UOM", "")

    # -- Packaging dims ------------------------------------------------------------
    for axis_col, key in (("LENGTH", "LENGTH"), ("HEIGHT", "HEIGHT"), ("WIDTH", "WIDTH")):
        v = pkg.get(key, "")
        if v:
            out[key] = v
            out[f"{key}_UOM"] = pkg.get(f"{key}_UOM", "")

    # -- Digital assets (deterministic constructed names, R-AST-01) ---------------
    brand_line = (row.get("brand_name") or row.get("manufacturer_name") or "")
    assets = name_assets(brand_line, mpn) if brand_line and mpn else {}
    for col, fname in assets.items():
        out[col] = fname
    out["Actual Image (Yes/No)"] = actual_image_flag(assets)

    return out


def fix_row(out_row: dict) -> list:
    """Apply deterministic rebuilds for validator failures; return issues after fix."""
    from .validate import fix_invoice, fix_mobile, validate_output_row

    issues = validate_output_row(out_row)
    for iss in issues:
        if iss.column == "INVOICE_DESC" and iss.code == "CHAR_LIMIT":
            out_row["INVOICE_DESC"] = fix_invoice(out_row["INVOICE_DESC"])
        elif iss.column == "MOBILE_DESC" and iss.code == "CHAR_LIMIT":
            out_row["MOBILE_DESC"] = fix_mobile(out_row["MOBILE_DESC"])
    return validate_output_row(out_row)


def write_outputs(rows: list[dict], audits: list[dict], out_dir: str | Path) -> dict:
    """Write output.xlsx, output.csv, audit_report.xlsx. Returns file paths."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    headers = load_expected_headers()

    data = [[r.get(h, "") for h in headers] for r in rows]
    df = pd.DataFrame(data, columns=headers)

    xlsx_path = out_dir / "output.xlsx"
    csv_path = out_dir / "output.csv"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as xw:
        df.to_excel(xw, index=False, sheet_name="Output")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)

    audit_rows = []
    for a in audits:
        audit_rows.append({
            "row": a.get("row", ""),
            "MPN": a.get("mpn", ""),
            "NEEDS_REVIEW": "YES" if a.get("flag") else "",
            "reason_codes": ";".join(a.get("reasons", [])),
            "identity_confidence": a.get("identity_conf", ""),
            "identity_signal": a.get("signal", ""),
            "classpath": a.get("classpath", ""),
            "classpath_verified": "YES" if a.get("classpath_verified") else "",
            "attr_count": a.get("attr_count", 0),
            "llm_enriched": "YES" if a.get("llm") else "",
            "validator_issues": "; ".join(str(i) for i in a.get("issues", []))[:500],
            "duplicate_flag": a.get("dup", ""),
        })
    adf = pd.DataFrame(audit_rows)
    audit_path = out_dir / "audit_report.xlsx"
    with pd.ExcelWriter(audit_path, engine="openpyxl") as aw:
        adf.to_excel(aw, index=False, sheet_name="Row Audit")

    # header equality assertion (R-HON-03): read back and compare
    back = next(csv.reader(open(csv_path, encoding="utf-8-sig")))
    assert back == headers, "EMITTED HEADERS DRIFTED FROM EXPECTED 252"

    return {"xlsx": xlsx_path, "csv": csv_path, "audit": audit_path}
