"""S6 — Digital assets & references: deterministic naming + MFR URL patterns.

R-SRC-01..03, R-AST-01..03. Manufacturer-owned domains only.
"""
from __future__ import annotations

import re


def _file_safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9\-_.]", "", (text or "").replace(" ", "_"))


def name_assets(brand: str, mpn: str) -> dict:
    """Deterministic filenames. Brand without ® in filenames (R-AST-01)."""
    b = _file_safe(brand.replace("®", "").replace("™", "").upper())
    m = _file_safe(mpn.upper())
    return {
        "Product Image": f"{b}_{m}.jpg",
        "Alternate Image 1": f"{b}_{m}_1.jpg",
        "Alternate Image 2": f"{b}_{m}_2.jpg",
        "Alternate Image 3": f"{b}_{m}_3.jpg",
        "Alternate Image 4": f"{b}_{m}_4.jpg",
    }


def doc_filename(brand: str, mpn: str, doc_type: str) -> str:
    """{BRAND}_{MPN}_{DocType}.pdf for evidenced doc types only."""
    b = _file_safe(brand.replace("®", "").replace("™", "").upper())
    m = _file_safe(mpn.upper())
    d = _file_safe(doc_type.replace("/", "_"))
    return f"{b}_{m}_{d}.pdf"


def mfr_url(domain: str, mpn: str) -> str:
    """Manufacturer product/support URL pattern (R-SRC-02)."""
    if not domain:
        return ""
    return f"https://www.{domain}/en/p/{mpn}"


def ref_urls(domain: str) -> list[str]:
    """Ref URLs = manufacturer-owned documentation pages only (R-SRC-03)."""
    if not domain:
        return []
    return [f"https://www.{domain}/support/documents"]


def actual_image_flag(asset_names: dict) -> str:
    return "Yes" if asset_names.get("Product Image") else "No"
