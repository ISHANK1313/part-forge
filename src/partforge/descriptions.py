"""S4 — Description building: deterministic template composer (R-DESC-01..06).

Templates compose first from validated structured fields; the LLM only fills
MARKETING_DESCRIPTION (optional). Char limits enforced by deterministic
trim/rebuild — never by hoping the LLM behaves.
"""
from __future__ import annotations

import re

INVOICE_MAX = 40
MOBILE_MIN, MOBILE_MAX = 60, 80

_MATERIAL_ABBR = {
    "stainless steel": "SST", "steel": "STL", "aluminum": "AL",
    "aluminium": "AL", "plastic": "PLS", "brass": "BRS", "bronze": "BRZ",
    "carbon steel": "CRB STL", "ceramic": "CER", "silicon carbide": "SiC",
    "aluminum oxide": "AO", "zirconia alumina": "ZR",
}


def _material_abbr(material: str) -> str:
    m = material.lower()
    for full, abbr in _MATERIAL_ABBR.items():
        if full in m:
            return abbr
    return material.upper()[:3]


def _clean(s: str | None) -> str:
    return re.sub(r"\s+", " ", (s or "").strip()).strip(" ,")


def _attr(row: dict, label: str) -> str:
    for t in row.get("_attributes") or []:
        if t.get("label") == label:
            return str(t.get("value", ""))
    return ""


def _invoice_desc(row: dict, item_type: str) -> str:
    """ALL CAPS ≤40: {TYPE} {MOUNT} {SIZE/QTY} {MAT} {ELEC} {DIM}. Compressed units."""
    parts = [item_type.upper()]
    mount = _attr(row, "Mounting Type")
    if mount:
        parts.append(mount.split()[0].upper())
    size = _attr(row, "Size")
    grit = _attr(row, "Grit")
    if size:
        parts.append(size.replace(" in x ", "X").replace(" in", "").upper())
    if grit:
        parts.append(f"P{grit}")
    mat = _attr(row, "Material")
    if mat:
        parts.append(_material_abbr(mat))
    volts, amps = _attr(row, "Voltage Rating"), _attr(row, "Amperage Rating")
    elec = ""
    if volts:
        elec += f"{volts}V"
    if amps:
        elec += f" {amps}A" if elec else f"{amps}A"
    if elec:
        parts.append(elec)
    sound = _attr(row, "Sound Level")
    if sound:
        parts.append(f"{sound}DBA")
    depth = _attr(row, "Depth With Door Open")
    if depth:
        parts.append(f"{depth.replace(' ', '')}IN")

    text = " ".join(p for p in parts if p)
    # trim least-significant tail tokens until within limit
    while len(text) > INVOICE_MAX and len(parts) > 1:
        parts.pop()
        text = " ".join(parts)
    return text[:INVOICE_MAX].strip()


def _mobile_desc(row: dict, item_type: str) -> str:
    """60–80 chars: {MANUFACTURER} {BRAND}, {Item Type}, {Series}, {MPN}[, filler]."""
    mfr = _clean(row.get("manufacturer_name"))
    brand = _clean(row.get("brand_name")).replace("®", "").replace("™", "")
    series = _clean(row.get("series"))
    mpn = _clean(row.get("mpn")) or _clean(row.get("Mfg_Part_Num"))

    lead = brand if brand.lower() == mfr.lower() else f"{mfr} {brand}".strip()
    base_parts = [p for p in [lead, item_type, series, mpn] if p]
    pkg = row.get("_packaging") or {}
    qty, uom = pkg.get("Selling Qty", ""), pkg.get("Selling UOM", "")
    fillers = [
        _attr(row, "Mounting Type"),
        _attr(row, "Material"),
        _attr(row, "Color"),
        (_attr(row, "Grit") or "") and f"P{_attr(row, 'Grit')} Grit",
        (_attr(row, "Size") or ""),
        f"{qty} per {uom}" if qty and uom else "",
    ]
    fi = 0
    while len(", ".join(base_parts)) < MOBILE_MIN and fi < len(fillers):
        nxt = _clean(fillers[fi])
        fi += 1
        if not nxt or any(nxt.lower() == p.lower() for p in base_parts):
            continue
        base_parts.insert(-1 if mpn else len(base_parts), nxt)
    text = ", ".join(base_parts)
    if len(text) > MOBILE_MAX:
        drop = [i for i, p in enumerate(base_parts) if series and p == series]
        if drop:
            base_parts.pop(drop[0])
            text = ", ".join(base_parts)
    return text


def _short_desc(row: dict, item_type: str) -> str:
    """{BRAND®} {Series} {MPN} {Type} With {feature}, {attr}, …"""
    brand = _clean(row.get("brand_name"))
    series = _clean(row.get("series"))
    mpn = _clean(row.get("mpn")) or _clean(row.get("Mfg_Part_Num"))
    feature = _clean(row.get("with_feature"))
    attrs = _display_attrs(row)
    head = " ".join(p for p in [brand, series, mpn, item_type] if p)
    mid = f" With {feature}" if feature else ""
    tail = f", {', '.join(attrs)}" if attrs else ""
    return f"{head}{mid}{tail}"


def _long_desc(row: dict, item_type: str) -> str:
    """{BRAND®} {Type} With {feature}, {Series}, specs… Additional Information: …"""
    brand = _clean(row.get("brand_name"))
    series = _clean(row.get("series"))
    feature = _clean(row.get("with_feature"))
    specs: list[str] = []

    def spec(text: str) -> None:
        t = _clean(text)
        if t and t not in specs:
            specs.append(t)

    volts, amps = _attr(row, "Voltage Rating"), _attr(row, "Amperage Rating")
    if volts:
        e = f"{volts} V"
        if amps:
            e += f", {amps} A"
        spec(e)
    mount = _attr(row, "Mounting Type")
    if mount:
        spec(f"{mount} Mounting")
    size = _attr(row, "Size")
    if size:
        spec(size)
    depth, duom = _attr(row, "Depth With Door Open"), _uom_of(row, "Depth With Door Open")
    if depth:
        spec(f"{depth} {duom}".strip())
    sound = _attr(row, "Sound Level")
    if sound:
        spec(f"{sound} dBA Sound Level")
    for lbl in ["Material", "Color"]:
        v = _attr(row, lbl)
        if v:
            spec(v)

    extras = _clean(row.get("additional_info"))
    head = " ".join(p for p in [brand, item_type] if p)
    mid = f" With {feature}," if feature else ","
    ser = f" {series}," if series else ""
    addl = f" Additional Information: {extras}." if extras else "."
    return f"{head}{mid}{ser} " + ", ".join(specs) + addl


def _retail_desc(row: dict, item_type: str) -> str:
    """Compact retail line, no brand prefix required."""
    series = _clean(row.get("series"))
    attrs = _display_attrs(row)
    head = " ".join(p for p in [series, item_type] if p)
    return f"{head}, {', '.join(attrs)}" if attrs else head


def _display_attrs(row: dict) -> list[str]:
    out: list[str] = []
    for t in row.get("_attributes") or []:
        lbl, val, uom = t.get("label"), t.get("value"), t.get("uom")
        if not val or lbl in ("Model",):
            continue
        text = f"{val} {uom}".strip() if uom else str(val)
        out.append(text)
    seen: set[str] = set()
    dedup: list[str] = []
    for a in out:
        k = a.lower()
        if k not in seen:
            seen.add(k)
            dedup.append(a)
    return dedup[:6]


def _uom_of(row: dict, label: str) -> str:
    for t in row.get("_attributes") or []:
        if t.get("label") == label:
            return str(t.get("uom") or "")
    return ""


def build(row: dict) -> dict:
    """Compose all six description fields for one enriched row dict."""
    item_type = row.get("item_type") or "Product"
    return {
        "INVOICE_DESC": _invoice_desc(row, item_type),
        "MOBILE_DESC": _mobile_desc(row, item_type),
        "SHORT_DESC": _short_desc(row, item_type),
        "LONG_DESC1": _long_desc(row, item_type),
        "RETAIL_DESC": _retail_desc(row, item_type),
        "MARKETING_DESCRIPTION": _clean(row.get("marketing_description")),
    }
