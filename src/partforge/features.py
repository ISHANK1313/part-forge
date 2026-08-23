"""S5 — Features & extras: series detection, flagship feature, LLM enrichment.

R-FEA-01, R-MISC-01, R-HON-01: empty-if-unsure; never invent claims.
"""
from __future__ import annotations

import re

from . import llm
from .normalise import title_case

_SERIES_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9]*(?:[ -][A-Z][A-Za-z0-9_]*){0,2})\s+(Series|Line|Collection)\b"
)


def deterministic_series(text: str) -> str:
    m = _SERIES_RE.search(text or "")
    if not m:
        return ""
    return f"{m.group(1)} {m.group(2)}"


def llm_enrich(row: dict) -> dict | None:
    """One constrained LLM call for evidence-backed soft fields."""
    if not llm.available():
        return None
    from .prompts_loader import render_prompt

    context = {
        k: v for k, v in {
            "Mfg_Part_Num": row.get("Mfg_Part_Num", ""),
            "Part_Desc": row.get("_desc_clean") or row.get("Part_Desc", ""),
            "Part_Manuf": row.get("Part_Manuf", ""),
            "manufacturer_name": row.get("manufacturer_name", ""),
            "brand_name": row.get("brand_name", ""),
            "item_type": row.get("item_type", ""),
        }.items() if v
    }
    prompt = render_prompt("features", {"row": context})
    resp = llm.call_json("features", prompt)
    if not isinstance(resp, dict):
        return None
    return resp


def apply(row: dict, *, use_llm: bool = True, shared: dict | None = None) -> dict:
    """Merge deterministic + LLM enrichment into the working row dict.

    `shared` may carry a pre-fetched combined enrichment response (see enrich.py);
    keys are identical to prompts/features.md output.
    """
    desc = row.get("_desc_clean") or row.get("Part_Desc") or ""

    series = deterministic_series(desc)
    enriched: dict | None = shared
    if enriched is None and use_llm:
        enriched = llm_enrich(row)

    def pick(key: str, current: str = "") -> str:
        if current:
            return current
        if enriched:
            val = enriched.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        return ""

    row["_series"] = pick("series", series)
    row["series"] = row["_series"]
    row["with_feature"] = pick("with_feature")
    row.setdefault("_attributes", [])
    labels = {t.get("label") for t in row["_attributes"]}

    def ensure_attr(label: str, key: str) -> None:
        val = pick(key)
        if val and label not in labels:
            row["_attributes"].append({"label": label, "value": val, "uom": ""})
            labels.add(label)
        elif val and label in labels:
            for t in row["_attributes"]:
                if t.get("label") == label and not t.get("value"):
                    t["value"] = val

    ensure_attr("Mounting Type", "mounting_type")
    ensure_attr("Material", "material")
    ensure_attr("Color", "color")

    features = []
    if enriched:
        raw = enriched.get("features") or []
        features = [str(f).strip() for f in raw
                    if isinstance(f, str) and f.strip()][:20]
    row["features"] = features
    row["approvals"] = [str(a).strip() for a in (enriched or {}).get("approvals", [])
                        if isinstance(a, str) and a.strip()]
    w = (enriched or {}).get("warranty")
    row["warranty"] = w.strip() if isinstance(w, str) else ""
    mk = (enriched or {}).get("marketing_description")
    row["marketing_description"] = mk.strip() if isinstance(mk, str) else ""
    ai = (enriched or {}).get("additional_information")
    row["additional_info"] = ai.strip() if isinstance(ai, str) else ""
    app = (enriched or {}).get("application")
    row["application"] = app.strip() if isinstance(app, str) and app.strip() else ""
    inc = (enriched or {}).get("includes", "")
    if isinstance(inc, list):
        inc = ", ".join(str(i) for i in inc)
    row["includes"] = inc.strip() if isinstance(inc, str) else ""
    row["_llm_enriched"] = bool(enriched)
    return row


def product_title(item_type: str) -> str:
    """R-MISC-01: Product Name = generic item type."""
    return title_case(item_type) if item_type else ""
