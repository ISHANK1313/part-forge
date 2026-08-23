"""Combined S3+S5 LLM enrichment — ONE call per row.

Provider latency measured ~42 s/call regardless of model (llm.py note), so calls
are precious: this single call returns attribute triplets AND soft fields together,
then attributes.extract(shared=...) and features.apply(shared=...) consume them.
"""
from __future__ import annotations

from . import llm
from .lookups import ATTRIBUTE_LABELS


def build_context(row: dict) -> dict:
    keep: dict = {}
    skip_prefixes = ("_",)
    for k, v in row.items():
        if k.startswith(skip_prefixes):
            continue
        if isinstance(v, (str, int, float)):
            keep[k] = v
        elif isinstance(v, dict):
            keep[k] = {kk: vv for kk, vv in v.items()
                       if isinstance(vv, (str, int, float))}
    # prefer cleaned description when available
    if row.get("_desc_clean"):
        keep["Part_Desc"] = row["_desc_clean"]
    if row.get("_mfr_clean"):
        keep["Part_Manuf"] = row["_mfr_clean"]
    return keep


def enrich_row(row: dict, existing_labels: list[str]) -> dict | None:
    """Return combined enrichment dict or None (no key / failure / bad shape)."""
    if not llm.available():
        return None
    from .prompts_loader import render_prompt

    context = {
        "Mfg_Part_Num": row.get("Mfg_Part_Num", ""),
        "Part_Desc": row.get("_desc_clean") or row.get("Part_Desc", ""),
        "E1_Brand": row.get("E1_Brand", ""),
        "Unilog_Brand": row.get("Unilog_Brand", ""),
        "DIB_Brand": row.get("DIB_Brand", ""),
        "Part_Manuf": row.get("Part_Manuf", ""),
        "manufacturer_name": row.get("manufacturer_name", ""),
        "brand_name": row.get("brand_name", ""),
        "item_type": row.get("item_type", ""),
    }
    context = {k: v for k, v in context.items() if v}
    prompt = render_prompt("enrich", {
        "row": context,
        "labels": ATTRIBUTE_LABELS,
        "existing": existing_labels,
    })
    resp = llm.call_json("enrich", prompt)
    return resp if isinstance(resp, dict) else None
