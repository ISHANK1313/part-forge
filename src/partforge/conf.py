"""Confidence model (architecture.md §4).

confidence = base(method) × validator_pass × source_strength
"""
from __future__ import annotations

METHOD_BASE = {
    "deterministic_lookup": 0.95,
    "regex_parse": 0.85,
    "constrained_llm": 0.75,
    "free_llm": 0.55,
    "inferred": 0.35,
}

CRITICAL_FIELDS = ("manufacturer_name", "brand_name", "classpath", "item_type")
ATTR_UNRESOLVED_THRESHOLD = 0.30
REVIEW_CONFIDENCE = 0.6


def field_confidence(method: str, validator_pass: bool,
                     source_strength: float = 1.0) -> float:
    base = METHOD_BASE.get(method, 0.5)
    return round(base * (1.0 if validator_pass else 0.5) * source_strength, 2)


def needs_review(identity_conf: float, classpath_verified: bool,
                 attr_total: int) -> tuple[bool, str]:
    """Return (flag, reason code) for row-level NEEDS_REVIEW."""
    if identity_conf < REVIEW_CONFIDENCE:
        return True, "LOW_IDENTITY_CONFIDENCE"
    if not classpath_verified:
        return True, "CLASSPATH_UNVERIFIED"
    return False, ""
