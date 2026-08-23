"""S1 — Identity resolution via signal vote (R-ID-01..06).

Signals in priority order: description tokens > MPN prefix > supplier fuzzy.
"""
from __future__ import annotations

import re

from rapidfuzz import fuzz

from .lookups import BrandEntry, lookup_brand
from .normalise import strip_supplier_code


def _desc_tokens(desc: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9&.\-]*", desc or "")


def _iter_master():
    from .lookups import BRAND_MASTER
    yield from BRAND_MASTER.items()


def _match_desc_tokens(tokens: list[str]) -> tuple[BrandEntry | None, str]:
    """Exact alias-token match inside description tokens."""
    for tok in tokens:
        hit = lookup_brand(tok.rstrip(".,"))
        if hit:
            return hit, f"desc_token:{tok}"
    joined = " " + " ".join(t.lower() for t in tokens) + " "
    for token, entry in _iter_master():
        if len(token) > 3 and f" {token} " in joined:
            return entry, f"desc_phrase:{token}"
    return None, ""


def _match_mpn_prefix(mpn: str) -> tuple[BrandEntry | None, str]:
    mpn_u = (mpn or "").upper()
    for token, entry in _iter_master():
        for prefix in entry.mpn_prefixes:
            if prefix.upper() in mpn_u and mpn_u.find(prefix.upper()) == 0:
                return entry, f"mpn_prefix:{prefix}"
    return None, ""


def _match_supplier(supplier: str) -> tuple[BrandEntry | None, str, int]:
    """Fuzzy-match supplier string against manufacturer legal names."""
    s = strip_supplier_code(supplier) or ""
    best: tuple[BrandEntry | None, int] = (None, 0)
    seen_names: set[str] = set()
    for _, entry in _iter_master():
        if entry.manufacturer in seen_names:
            continue
        seen_names.add(entry.manufacturer)
        score = max(
            fuzz.ratio(s.lower(), entry.manufacturer.lower()),
            fuzz.partial_ratio(entry.brand.replace("®", "").replace("™", "").lower(), s.lower()),
        )
        if score > best[1]:
            best = (entry, int(score))
    entry, score = best
    return entry, f"supplier_fuzzy:{score}", score


def resolve(row: dict) -> dict:
    """Vote identity for one cleaned row.

    Returns {manufacturer_name, brand_name, trade_name, confidence, signal}.
    """
    desc = row.get("_desc_clean") or row.get("Part_Desc") or ""
    mpn = row.get("Mfg_Part_Num") or ""
    supplier = row.get("_mfr_clean") or row.get("Part_Manuf") or ""

    signals: list[tuple[float, BrandEntry, str]] = []

    entry, why = _match_desc_tokens(_desc_tokens(desc))
    if entry:
        signals.append((0.95, entry, why))

    entry, why = _match_mpn_prefix(mpn)
    if entry:
        signals.append((0.80, entry, why))

    sentry, why, score = _match_supplier(supplier)
    if sentry and score >= 85:
        signals.append((min(score / 100 * 0.7, 0.65), sentry, why))

    if not signals:
        return {"manufacturer_name": "", "brand_name": "", "trade_name": "",
                "confidence": 0.0, "signal": "none", "domain": ""}

    signals.sort(key=lambda t: t[0], reverse=True)
    conf, top, signal = signals[0]
    if len(signals) > 1 and signals[1][1].manufacturer == top.manufacturer:
        conf = min(conf + 0.05, 0.99)

    brand_line = top.brand or top.manufacturer   # R-ID-05
    return {
        "manufacturer_name": top.manufacturer,
        "brand_name": brand_line,
        "trade_name": "",                            # R-ID-06: never fabricate
        "confidence": round(conf, 2),
        "signal": signal,
        "domain": top.domain,
    }
