"""Deterministic normalisers: placeholders, inch fractions, units, dimensions.

Pure functions — heavily unit-tested. Implements rules.md R-CLEAN-01/02,
R-UOM-01/02/03.
"""
from __future__ import annotations

import re
from fractions import Fraction

PLACEHOLDERS = {
    "-- unbranded --",
    "-- no unilog brand --",
    "-- no dib brand --",
}

_MixedNumRe = re.compile(r"^(\d+)-(\d+)/(\d+)$")


def strip_placeholder(value: str | None) -> str | None:
    """R-CLEAN-01: placeholder or blank -> None."""
    if value is None:
        return None
    v = value.strip()
    if not v or v.lower() in PLACEHOLDERS:
        return None
    return v


def strip_supplier_code(value: str | None) -> str | None:
    """R-CLEAN-02: 'Freud Inc (2435)' -> 'Freud Inc'."""
    v = strip_placeholder(value)
    if v is None:
        return None
    return re.sub(r"\s*\([^)]*\)\s*$", "", v).strip()


def _nearest_trade_frac(rem: float) -> tuple[int, int]:
    """Closest fraction with a power-of-2 denominator (2..64) to rem in [0,1)."""
    best: tuple[int, int] = (0, 1)
    best_err = rem
    for den in (2, 4, 8, 16, 32, 64):
        for num in {1, round(rem * den)}:
            if not 0 < num <= den:
                continue
            err = abs(rem - num / den)
            if err < best_err - 1e-12:
                best, best_err = (num, den), err
    return best


def dec_to_fraction(value: float | str) -> str:
    """R-UOM-02: decimal inches -> trade fraction.

    0.5 -> '1/2'; 50.25 -> '50-1/4'; 8.5 -> '8-1/2'; whole stays '24'.
    Power-of-2 denominators only (trade rule); .045 -> 3/64.
    """
    if isinstance(value, str):
        s = value.strip()
        if _MixedNumRe.match(s):
            return s
        try:
            value = float(s)
        except ValueError:
            return s.strip()
    neg = value < 0
    value = abs(value)
    whole = int(value)
    num, den = _nearest_trade_frac(value - whole)
    if num == 0 or num == den:
        out = f"{whole + (1 if num == den else 0)}"
    elif whole:
        out = f"{whole}-{num}/{den}"
    else:
        out = f"{num}/{den}"
    return f"-{out}" if neg else out


def _approved_uom(raw: str) -> str | None:
    from .lookups import APPROVED_UOM
    key = raw.strip().strip(".").lower().replace("″", '"').replace("'", "")
    return APPROVED_UOM.get(key)


def normalize_unit(number_part: str, unit_raw: str, *, invoice_style: bool = False) -> str:
    """R-UOM-01/03: '24'+'in' -> '24 in' ('24IN' in invoice style)."""
    uom = _approved_uom(unit_raw)
    if uom is None:
        return f"{number_part} {unit_raw}".strip()
    if invoice_style:
        return f"{number_part}{uom.upper()}"
    return f"{number_part} {uom}"


_FractionInDesc = re.compile(
    r"(\d+(?:\.\d+)?)[-\s]?(\d+/(\d+))?\s*(in|inch|inches|mm|ft|\"|″)(?![A-Za-z])",
    re.IGNORECASE,
)


def fractions_to_trade(text: str) -> str:
    """Rewrite '5"x18"' / '.045 in' / '7/8 in' with approved spacing/fractions."""

    def repl(m: re.Match) -> str:
        num = float(m.group(1))
        frac = m.group(2)
        uom = _approved_uom(m.group(4)) or m.group(4)
        if frac:
            whole_part = int(num) if num >= 1 else ""
            _, _, den = frac.partition("/")
            numer = frac.split("/")[0]
            base = f"{whole_part}-{numer}/{den}" if whole_part else f"{numer}/{den}"
            return f"{base} {uom}"
        if num == int(num):
            return f"{int(num)} {uom}"
        return f"{dec_to_fraction(num)} {uom}"

    return _FractionInDesc.sub(repl, text)


def parse_number_token(tok: str) -> str:
    """Normalise a numeric token to fraction form ('50.25'->'50-1/4', '7/8' stays)."""
    tok = tok.strip()
    if "/" in tok or "-" in tok:
        return tok
    try:
        val = float(tok)
    except ValueError:
        return tok
    if val == int(val):
        return str(int(val))
    return dec_to_fraction(val)


_DIM_TOKEN = re.compile(
    r"(?P<num>\d+(?:-\d+/\d+|\.\d+|/\d+)?)\s*"
    r"(?P<uom>in\.?|inch(?:es)?|mm|cm|m\b|ft|feet|[\"″])?",
    re.IGNORECASE,
)


def parse_dims(text: str) -> list[dict]:
    """Extract dimension tokens from text.

    Returns [{'axis': 'L'|'W'|'D'|'H'|'', 'value': fraction-str, 'uom': approved}]
    Axis inferred from an adjacent trailing letter hint (W/D/H/L) when present.
    """
    results: list[dict] = []
    for m in _DIM_TOKEN.finditer(text):
        uom_raw = (m.group("uom") or "").strip().rstrip(".")
        uom = _approved_uom(uom_raw) if uom_raw else ""
        if not uom:
            continue
        num = parse_number_token(m.group("num"))
        axis = ""
        tail = text[m.end():m.end() + 3].lstrip()
        if tail and tail[0].upper() in "WDHL":
            axis = tail[0].upper()
        results.append({"axis": axis, "value": num, "uom": uom})
    return results


_PACK_RE = re.compile(r"(\d+)\s*[- ]?\s*(pc|pcs|piece|pieces|pack|box|discs?/box|belts?/box)\b", re.IGNORECASE)


def parse_pack_count(text: str) -> tuple[str, str] | None:
    """R-PKG-01: '6pc', '50 Disc/Box' -> ('6', 'pc'|'Box') else None."""
    m = _PACK_RE.search(text)
    if not m:
        return None
    qty = m.group(1)
    kind = m.group(2).lower()
    if "box" in kind:
        return qty, "Box"
    if "pack" in kind:
        return qty, "Pack"
    return qty, "pc"


def title_case(text: str) -> str:
    """Title Case that keeps known acronyms intact."""
    small = {"and", "or", "with", "of", "the", "a", "an", "for", "in", "to"}
    caps = {"SS", "RPM", "V", "A", "W", "HP", "PSI", "3M", "GE", "LG", "SDS"}
    out = []
    for i, word in enumerate(text.split()):
        if word.upper() in caps:
            out.append(word.upper())
        elif word.lower() in small and i > 0:
            out.append(word.lower())
        else:
            out.append(word[:1].upper() + word[1:] if word else word)
    return " ".join(out)
