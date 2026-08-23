"""S0 — Ingest & cleanse (FR-01, R-CLEAN-01/02/04)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

INPUT_COLUMNS = ["Mfg_Part_Num", "Part_Desc", "E1_Brand", "Unilog_Brand",
                 "DIB_Brand", "Part_Manuf"]


class InputError(Exception):
    pass


def load_input(path: str | Path) -> pd.DataFrame:
    """Load raw input CSV/XLSX into a DataFrame.

    - Tolerates BOM, embedded quotes, extra unknown columns.
    - Keeps original passthrough values untouched (gold rows show placeholders
      copied verbatim); adds internal cleaned columns for pipeline use.
    """
    path = Path(path)
    if not path.exists():
        raise InputError(f"Input file not found: {path}")
    try:
        if path.suffix.lower() in {".xlsx", ".xls"}:
            df = pd.read_excel(path, dtype=str)
        else:
            df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    except Exception as exc:
        raise InputError(f"Could not parse input file {path}: {exc}") from exc

    missing = [c for c in INPUT_COLUMNS if c not in df.columns]
    if missing:
        raise InputError(f"Input is missing required columns: {missing}")

    from .normalise import strip_placeholder, strip_supplier_code

    df = df.copy()
    df["_desc_clean"] = df["Part_Desc"].map(strip_placeholder)
    df["_mfr_clean"] = df["Part_Manuf"].map(strip_supplier_code)
    for col in ["E1_Brand", "Unilog_Brand", "DIB_Brand"]:
        df[f"_{col.lower()}_clean"] = df[col].map(strip_placeholder)

    # R-CLEAN-04: exact duplicate MPN+desc rows -> keep first, flag rest.
    dup_mask = df.duplicated(subset=["Mfg_Part_Num", "Part_Desc"], keep="first")
    df["_dup_flag"] = ""
    df.loc[dup_mask, "_dup_flag"] = "DUPLICATE_OF_EARLIER_ROW"
    df.attrs["duplicate_rows"] = int(dup_mask.sum())
    return df
