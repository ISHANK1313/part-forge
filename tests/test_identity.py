"""Identity resolution tests (S1 signal vote) against known sample rows."""
from partforge.identity import resolve


def test_desc_token_beats_all():
    out = resolve({"Part_Desc": '49-94-0013 Milw 5"x.045"x7/8" Metal Cut Off Disc',
                   "Mfg_Part_Num": "49-94-0013",
                   "Part_Manuf": "Jam Industrial Supply LLC (JAMIN)"})
    assert out["manufacturer_name"] == "Milwaukee Tool"
    assert out["brand_name"].startswith("Milwaukee")
    assert out["confidence"] >= 0.9
    assert out["domain"] == "milwaukeetool.com"


def test_mpn_prefix_signal():
    out = resolve({"Part_Desc": "PDSH4816AF Dishwasher SS - Display Only",
                   "Mfg_Part_Num": "PDSH4816AF",
                   "Part_Manuf": "Appliance Dealers Cooperative (APPDE)"})
    assert out["manufacturer_name"] == "Rheem Manufacturing"   # gold row 1
    assert out["brand_name"] == "FRIGIDAIRE®"                  # exact casing + mark


def test_whirlpool_gold():
    out = resolve({"Part_Desc": "WDTS7024RZ Dishwasher SS - Display Only",
                   "Mfg_Part_Num": "WDTS7024RZ",
                   "Part_Manuf": "Appliance Dealers Cooperative (APPDE)"})
    assert out["manufacturer_name"] == "Whirlpool Corporation"
    assert out["brand_name"] == "Whirlpool®"


def test_unknown_row_flags_low():
    out = resolve({"Part_Desc": "widget thing", "Mfg_Part_Num": "ZZZ-1",
                   "Part_Manuf": ""})
    assert out["confidence"] < 0.6 and out["signal"] == "none"
