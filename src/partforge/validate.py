"""S8 — Validators per rules.md IDs. Deterministic, per-cell issues list."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .lookups import APPROVED_UOM

REFERENCE_DIR = Path(__file__).resolve().parents[2] / "reference"
EXPECTED_HEADERS_PATH = REFERENCE_DIR / "expected_headers.csv"

INVOICE_MAX = 40
MOBILE_MIN, MOBILE_MAX = 60, 80


@dataclass
class Issue:
    column: str
    code: str
    detail: str

    def __str__(self) -> str:
        return f"{self.column}: {self.code} — {self.detail}"


def load_expected_headers() -> list[str]:
    with open(EXPECTED_HEADERS_PATH, encoding="utf-8-sig", newline="") as fh:
        return next(csv.reader(fh))


def validate_output_row(out: dict) -> list[Issue]:
    """Validate one output row dict (keyed by the 252 headers)."""
    issues: list[Issue] = []

    invoice = out.get("INVOICE_DESC") or ""
    if invoice:
        if len(invoice) > INVOICE_MAX:
            issues.append(Issue("INVOICE_DESC", "CHAR_LIMIT", f"{len(invoice)} > 40"))
        if invoice != invoice.upper():
            issues.append(Issue("INVOICE_DESC", "CASING", "must be ALL CAPS"))

    mobile = out.get("MOBILE_DESC") or ""
    if mobile and not (MOBILE_MIN <= len(mobile) <= MOBILE_MAX):
        issues.append(Issue("MOBILE_DESC", "CHAR_LIMIT",
                            f"len={len(mobile)} not in [60,80]"))

    cp = out.get("Classpath") or ""
    if cp:
        for seg in cp.split(">"):
            if seg != seg.strip():
                issues.append(Issue("Classpath", "FORMAT",
                                    "spaces around '>' separator"))
                break

    approved_uoms = set(APPROVED_UOM.values())
    for col, val in out.items():
        if col.endswith("_UOM") and val and val not in approved_uoms:
            issues.append(Issue(col, "UOM_NOT_APPROVED", f"'{val}'"))

    for i in range(1, 51):
        lbl = out.get(f"ATTRIBUTE_LABEL {i}") or ""
        val = out.get(f"ATTRIBUTE_VALUE {i}") or ""
        uom = out.get(f"ATTRIBUTE_UOM {i}") or ""
        if lbl and not val:
            issues.append(Issue(f"ATTRIBUTE_LABEL {i}", "VALUE_MISSING", lbl))
        if uom and uom not in approved_uoms:
            issues.append(Issue(f"ATTRIBUTE_UOM {i}", "UOM_NOT_APPROVED", uom))
        if uom and not val:
            issues.append(Issue(f"ATTRIBUTE_UOM {i}", "UOM_WITHOUT_VALUE", uom))

    brand = out.get("BRAND_NAME") or ""
    if brand and "®" not in brand and "™" not in brand:
        # R-ID-03/R-CASE-01: approved names carry their marks (soft warning).
        issues.append(Issue("BRAND_NAME", "BRAND_MARK_MISSING", brand))

    return issues


def fix_invoice(text: str) -> str:
    """Deterministic rebuild: trim tail tokens then hard-cut to ≤40 CAPS."""
    t = text.upper().strip()
    while len(t) > INVOICE_MAX and " " in t:
        t = t.rsplit(" ", 1)[0]
    return t[:INVOICE_MAX].strip()


def fix_mobile(text: str) -> str:
    """Deterministic rebuild toward ≤80 by dropping middle comma segments.
    Never shrinks below MOBILE_MIN — a short mobile stays short (honest flag)."""
    parts = [p.strip() for p in text.split(",")]
    while len(", ".join(parts)) > MOBILE_MAX and len(parts) > 3:
        candidate = parts[: len(parts) - 2] + [parts[-1]]
        if len(", ".join(candidate)) < MOBILE_MIN:
            break
        parts = candidate
    return ", ".join(parts)
