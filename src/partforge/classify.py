"""S2 — Item-type extraction & classification (R-CLS-01..03).

Deterministic keyword extractor first; optional LLM refinement constrained to
taxonomy candidates.
"""
from __future__ import annotations

import re

from .lookups import TAXONOMY, classpath_for

# Ordered seed vocabulary: longest/most-specific phrases first.
_ITEM_TYPES = [
    ("cut off disc", "Cut-Off Disc"), ("cut-off disc", "Cut-Off Disc"),
    ("cut off wheel", "Cut-Off Wheel"), ("cut-off wheel", "Cut-Off Wheel"),
    ("grinding disc", "Grinding Disc"), ("grinding wheel", "Grinding Wheel"),
    ("flap disc", "Flap Disc"),
    ("sanding belt", "Sanding Belt"), ("abrasive belt", "Sanding Belt"),
    ("sanding disc", "Sanding Disc"),
    ("sandpaper", "Abrasive Sheet"), ("sanding sheet", "Abrasive Sheet"),
    ("wire wheel", "Wire Wheel"), ("wire brush", "Wire Brush"),
    ("drill bit", "Drill Bit"), ("saw blade", "Saw Blade"),
    ("hole saw", "Hole Saw"),
    ("dishwasher", "Dishwasher"),
    ("refrigerator", "Refrigerator"), ("fridge", "Refrigerator"),
    ("microwave", "Microwave Oven"),
    ("washing machine", "Washing Machine"),
    ("clothes dryer", "Clothes Dryer"), ("dryer", "Clothes Dryer"),
    ("range", "Range"), ("stove", "Range"), ("oven", "Oven"),
    ("pipe fitting", "Pipe Fitting"), ("fitting", "Fitting"),
    ("ball valve", "Ball Valve"), ("gate valve", "Gate Valve"), ("valve", "Valve"),
    ("hose", "Hose"),
    ("glove", "Gloves"), ("helmet", "Helmet"), ("hard hat", "Hard Hat"),
    ("safety glasses", "Safety Glasses"), ("goggles", "Goggles"),
    # observed sample categories
    ("decking", "Decking Board"), ("deck board", "Decking Board"),
    ("grooved deck", "Decking Board"), ("fascia", "Fascia Board"),
    ("baluster", "Baluster"), ("rail kit", "Railing Kit"),
    ("t-rail", "Railing Kit"), ("railing", "Railing"),
    ("fence", "Fencing"), ("gate", "Gate"),
    ("chandelier", "Chandelier"), ("pendant", "Pendant Light"),
    ("ceiling fan", "Ceiling Fan"), ("bulb", "Light Bulb"),
    ("incan", "Incandescent Bulb"), ("led", "LED Light"),
    ("outlet", "Outlet"), ("receptacle", "Receptacle"),
    ("sander", "Sander"), ("torx", "Drive Bit"),
    ("drive bit", "Drive Bit"), ("power bit", "Drive Bit"),
    ("pencil", "Mechanical Pencil"),
    # coarse single-noun fallbacks LAST (longer phrases above win)
    ("disc", "Sanding Disc"), ("belt", "Sanding Belt"),
    ("wheel", "Grinding Wheel"), ("brush", "Wire Brush"),
]


def extract_item_type(desc: str) -> tuple[str, float]:
    """Return (item_type, confidence) from the description text."""
    d = (desc or "").lower()
    if not d:
        return "", 0.0
    for kw, label in _ITEM_TYPES:
        if kw in d:
            return label, 0.85
    # plural fallback e.g. 'discs' -> 'disc'
    stripped = re.sub(r"\b(discs|wheels|belts|gloves)\b", lambda m: m.group(0)[:-1], d)
    for kw, label in _ITEM_TYPES:
        if kw in stripped:
            return label, 0.75
    return "", 0.0


def classify_row(row: dict) -> dict:
    """Deterministic classify for one row dict.

    Returns {item_type, item_type_confidence, classpath, classpath_verified}.
    """
    desc = row.get("_desc_clean") or row.get("Part_Desc") or ""
    item_type, conf = extract_item_type(desc)
    cp, verified = classpath_for(item_type) if item_type else ("", False)
    return {
        "item_type": item_type,
        "item_type_confidence": conf,
        "classpath": cp,
        "classpath_verified": verified,
    }


def candidate_classpaths(item_type: str) -> list[str]:
    """Taxonomy classpaths related to the item type (LLM constrained choice set)."""
    t = item_type.lower()
    out = []
    for keywords, cp in TAXONOMY:
        if any(k.split()[0][:4] in t or t in k for k in keywords):
            out.append(cp)
    return out or [cp for _, cp in TAXONOMY[:6]]
