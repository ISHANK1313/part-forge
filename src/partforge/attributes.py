"""S3 — Attribute extraction: deterministic regex parser first, LLM fills gaps.

Rules R-ATT-01..06, R-UOM-01/02. Labels constrained to ATTRIBUTE_LABELS or
strictly evidenced text; unresolvable triplets omitted entirely.
"""
from __future__ import annotations

import re

from . import llm
from .lookups import ATTRIBUTE_LABELS, approved_uom
from .normalise import dec_to_fraction, title_case

_LABEL_LOOKUP = {lbl.lower(): lbl for lbl in ATTRIBUTE_LABELS}


def _num(tok: str) -> str:
    v = float(tok)
    return str(int(v)) if v == int(v) else dec_to_fraction(v)


def _det_triplets(row: dict) -> list[dict]:
    """Regex-extract triplets from description + cleaned fields."""
    desc = row.get("_desc_clean") or row.get("Part_Desc") or ""
    out: list[dict] = []

    def add(label: str, value: str, uom: str) -> None:
        if value and not any(t["label"] == label for t in out):
            out.append({"label": label, "value": value, "uom": uom})

    m = re.search(r"(\d+(?:\.\d+)?)\s*[- ]?\s*(?:volts?|v)\b", desc, re.I)
    if m:
        add("Voltage Rating", _num(m.group(1)), "V")
    m = re.search(r"(\d+(?:\.\d+)?)\s*[- ]?\s*(?:amps?|a)\b(?!\w)", desc, re.I)
    if m:
        add("Amperage Rating", _num(m.group(1)), "A")
    m = re.search(r"(\d+)\s*dba\b", desc, re.I)
    if m:
        add("Sound Level", m.group(1), "dBA")
    m = re.search(r"(\d[\d,]*)\s*rpm\b", desc, re.I)
    if m:
        add("Maximum RPM", m.group(1).replace(",", ""), "rpm")
    m = re.search(r"\bP(\d{2,4})\b", desc)
    if m:
        add("Grit", m.group(1), "")
    m = re.search(r"(\d+(?:/\d+|\.\d+)?)\s*[- ]?\s*(?:arbor|bore)\b", desc, re.I)
    if m:
        add("Arbor Hole Size", dec_to_fraction(m.group(1)), "in")
    m = re.search(r"(\.\d+|\d+/\d+|-\d+/\d+)\s*(?:in|\"|″)?\s*(?:thick\b)", desc, re.I)
    if m:
        tok = m.group(1).lstrip("-")
        val = dec_to_fraction(tok) if "." in tok else tok
        add("Thickness", val, "in")

    # compound size strings like 5"x.045"x7/8" (3-part) or belts 1/2"x18" (2-part).
    # Inch marker REQUIRED per part (else MPN digits get captured); optional
    # leading dot so '.045"' doesn't lose its decimal point.
    parts = re.split(r"\s*(?:x|×)\s*", desc, maxsplit=3, flags=re.I)
    size_parts = []
    for p in parts[:3]:
        mm = re.search(r'(\.?\d+(?:-\d+/\d+|/\d+)?)\s*(?:["″]|in\b)', p, re.I)
        if not mm:
            break
        size_parts.append(dec_to_fraction(mm.group(1)))
    if len(size_parts) in (2, 3):
        uom = approved_uom("in") or "in"
        add("Size", f" {uom} x ".join(size_parts) + f" {uom}", "")

    series = row.get("_series")
    if series:
        add("Series", series, "")
    return out


def json_context(row: dict) -> str:
    return " | ".join(
        str(v) for k, v in row.items() if isinstance(v, str) and not k.startswith("__"))


def _row_context(row: dict) -> dict:
    keep = {}
    for k, v in row.items():
        if k.startswith("_dup"):
            continue
        if isinstance(v, (str, int, float)):
            keep[k] = v
        elif isinstance(v, dict):
            keep[k] = {kk: vv for kk, vv in v.items()
                       if isinstance(vv, (str, int, float))}
    return keep


def extract(row: dict, *, use_llm: bool = True, shared: dict | None = None) -> tuple[list[dict], float]:
    """Return (triplets, confidence). LLM adds evidenced labels not yet found.

    `shared` may carry a pre-fetched combined enrichment response (see enrich.py)
    to keep LLM calls at 1 per row (~42 s/call provider latency, llm.py note).
    """
    triplets = _det_triplets(row)

    conf = 0.85 if triplets else 0.5
    resp = shared
    if resp is None:
        if not use_llm or not llm.available():
            return triplets, conf
        from .prompts_loader import render_prompt
        prompt = render_prompt("attributes", {
            "row": _row_context(row),
            "labels": ATTRIBUTE_LABELS,
            "existing": [t["label"] for t in triplets],
        })
        resp = llm.call_json("attributes", prompt)
    if resp is None:
        return triplets, conf
    ctx = json_context(row).lower()

    added = 0
    for t in resp.get("triplets", [])[:50]:
        try:
            label = title_case(str(t.get("label", "")).strip())
            value = str(t.get("value", "")).strip()
            uom_raw = str(t.get("uom", "")).strip()
            evidence = str(t.get("evidence", "")).strip()
        except AttributeError:
            continue
        if not label or not value:
            continue
        canon = _LABEL_LOOKUP.get(label.lower())
        if canon is None:
            # allow only labels literally evidenced in row text (R-ATT-06)
            if label.lower() not in ctx:
                continue
            canon = label
        if any(x["label"] == canon for x in triplets):
            continue
        if evidence and evidence.lower() not in ctx:
            continue
        uom = approved_uom(uom_raw) if uom_raw else ""
        triplets.append({"label": canon, "value": value, "uom": uom or ""})
        added += 1
    return triplets[:50], min(conf + (0.05 if added else 0), 0.9)
