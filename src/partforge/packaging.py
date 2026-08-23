"""S7 — Commercial & packaging: pack counts, dims — evidence only (R-PKG-01/02)."""
from __future__ import annotations

from .normalise import parse_dims, parse_pack_count


def parse(row: dict) -> dict:
    """Extract selling qty/uom and package dims from description evidence.

    Only explicit single-axis hints (e.g. '18 in W') map to dim columns; bare
    compound size strings stay in attributes per R-ATT-03.
    """
    desc = row.get("_desc_clean") or row.get("Part_Desc") or ""
    out = {
        "Selling Qty": "", "Selling UOM": "",
        "LENGTH": "", "LENGTH_UOM": "",
        "WIDTH": "", "WIDTH_UOM": "",
        "HEIGHT": "", "HEIGHT_UOM": "",
    }

    pack = parse_pack_count(desc)
    if pack:
        out["Selling Qty"], out["Selling UOM"] = pack

    for d in parse_dims(desc):
        axis = d["axis"]
        col = {"L": "LENGTH", "W": "WIDTH", "H": "HEIGHT", "D": ""}.get(axis, "")
        if col and not out[col]:
            out[col] = d["value"]
            out[f"{col}_UOM"] = d["uom"]
    return out
