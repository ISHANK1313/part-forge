"""Scorer: PRD §5 metrics vs gold rows + rule-compliance rates.

Usage: python -m src.partforge.score --out out/
Writes metrics.md (deck-ready) and prints the table.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from partforge.lookups import APPROVED_UOM  # noqa: E402
from partforge.validate import load_expected_headers  # noqa: E402


def _norm(s: str) -> str:
    return (s or "").replace("®", "").replace("™", "").strip().casefold()


def score(out_csv: str) -> dict:
    headers = load_expected_headers()
    rows = list(csv.DictReader(open(out_csv, encoding="utf-8-sig")))
    n = len(rows)
    m: dict = {"rows": n, "headers": len(headers)}

    def pct(cond) -> float:
        return round(100.0 * sum(1 for r in rows if cond(r)) / max(n, 1), 1)

    m["invoice_le40_caps_%"] = pct(
        lambda r: r["INVOICE_DESC"] and r["INVOICE_DESC"] == r["INVOICE_DESC"].upper()
        and len(r["INVOICE_DESC"]) <= 40)
    m["mobile_60_80_%"] = pct(lambda r: r["MOBILE_DESC"] and 60 <= len(r["MOBILE_DESC"]) <= 80)
    m["classpath_populated_%"] = pct(lambda r: r["Classpath"])
    m["identity_populated_%"] = pct(lambda r: r["MANUFACTURER_NAME"] and r["BRAND_NAME"])
    uoms_ok, uoms_total = 0, 0
    approved = set(APPROVED_UOM.values())
    for r in rows:
        for i in range(1, 51):
            u = r.get(f"ATTRIBUTE_UOM {i}")
            if u:
                uoms_total += 1
                uoms_ok += u in approved
    m["approved_uom_%"] = round(100 * uoms_ok / uoms_total, 1) if uoms_total else 100.0
    attr_counts = [sum(1 for i in range(1, 51) if r.get(f"ATTRIBUTE_LABEL {i}")) for r in rows]
    m["avg_attrs_per_row"] = round(sum(attr_counts) / max(n, 1), 1)
    m["rows_with_attrs_%"] = pct(lambda r: any(
        r.get(f"ATTRIBUTE_LABEL {i}") for i in range(1, 4)))
    m["actual_image_yes_%"] = pct(lambda r: r["Actual Image (Yes/No)"] == "Yes")

    # ---- field-match vs the only verified gold pairs -------------------------
    gold_path = os.path.join("reference", "gold_rows.csv")
    gold = {g[11]: g for g in list(csv.reader(open(gold_path, encoding="utf-8-sig")))[1:]}
    checks = [("MANUFACTURER_NAME", _norm), ("BRAND_NAME", _norm),
              ("Classpath", lambda s: (s or "").strip())]
    matched, total = 0, 0
    details = {}
    for r in rows:
        g = gold.get(r["Mfg_Part_Num"])
        if not g:
            continue
        row_res = []
        gi = {h: g[i] for i, h in enumerate(headers)}
        for col, fn in checks:
            total += 1
            hit = fn(r[col]) == fn(gi[col]) and bool(fn(gi[col]))
            matched += hit
            row_res.append((col, "MATCH" if hit else "diff",
                            fn(r[col])[:45], fn(gi[col])[:45]))
        details[r["Mfg_Part_Num"]] = row_res
    m["gold_field_match_%"] = round(100 * matched / total, 1) if total else None
    return m, details


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out/")
    args = ap.parse_args()
    m, details = score(os.path.join(args.out, "output.csv"))

    lines = ["# PartForge Metrics (PRD §5)", "",
             "| Metric | Value | Target |", "|---|---|---|"]
    targets = {
        "headers": "252 exact", "invoice_le40_caps_%": "100", "mobile_60_80_%": "100",
        "classpath_populated_%": "≥90", "identity_populated_%": "≥90",
        "approved_uom_%": "≥95", "gold_field_match_%": "≥70 (verifiable fields)",
    }
    for k, v in m.items():
        lines.append(f"| {k} | {v} | {targets.get(k, '—')} |")
    table = "\n".join(lines)
    print(table)
    print()
    for mpn, res in details.items():
        print(f"gold {mpn}:")
        for col, verdict, got, want in res:
            print(f"  {verdict:5s} {col}: got={got!r} gold={want!r}")

    path = os.path.join(args.out, "metrics.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(table + "\n")
    print(f"\nwritten: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
