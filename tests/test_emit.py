"""Phase-0 gate tests: header equality + emission round-trip."""
import csv

from partforge.emit import assemble_row
from partforge.validate import load_expected_headers


def test_expected_headers_count():
    headers = load_expected_headers()
    assert len(headers) == 252
    assert headers[0] == "MFR URL"
    assert headers[-1] == "Actual Image (Yes/No)"
    assert headers[55] == "ATTRIBUTE_LABEL 1"
    assert headers[204] == "ATTRIBUTE_UOM 50"


def test_assemble_covers_all_headers():
    row = {
        "Mfg_Part_Num": "X1", "Part_Desc": "d", "E1_Brand": "-- Unbranded --",
        "Unilog_Brand": "-- No Unilog Brand --", "DIB_Brand": "",
        "Part_Manuf": "Supplier (SUP)",
        "manufacturer_name": "Milwaukee Tool", "brand_name": "Milwaukee®",
        "domain": "milwaukeetool.com", "classpath": "Abrasives>Cutting & Grinding>Cut-Off Wheels & Discs",
        "item_type": "Cut-Off Disc",
        "features": ["Fast cuts"], "with_feature": "Thin Kerf",
        "_attributes": [{"label": "Size", "value": '5 in x 3/64 in x 7/8 in', "uom": ""}],
        "_packaging": {"Selling Qty": "6", "Selling UOM": "pc"},
    }
    out = assemble_row(row)
    headers = load_expected_headers()
    assert set(out.keys()) == set(headers)
    assert out["MFR URL"].startswith("https://www.milwaukeetool.com")
    assert out["Part_Manuf"] == "Supplier (SUP)"          # passthrough verbatim
    assert out["With"] == "With Thin Kerf"
    assert out["Standard/Approvals"] == ""
    assert out["ATTRIBUTE_VALUE 1"].startswith("5 in")
    assert out["Product Image"] == "MILWAUKEE_X1.jpg"
    assert out["Actual Image (Yes/No)"] == "Yes"
    assert out["Selling Qty"] == "6"


def test_gold_mpn_present_in_sample():
    sample = list(csv.reader(open(
        "Unihack_ Sample Dataset - Input.csv", encoding="utf-8-sig")))
    mpns = {r[0] for r in sample[1:]}
    assert "PDSH4816AF" in mpns and "WDTS7024RZ" in mpns
