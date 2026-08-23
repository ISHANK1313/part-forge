"""Normaliser + classifier + validator unit tests (Phase 1/2 exit gates)."""
from partforge.classify import classify_row, extract_item_type
from partforge.lookups import classpath_for
from partforge.normalise import (dec_to_fraction, normalize_unit,
                                 parse_pack_count, strip_placeholder,
                                 strip_supplier_code)
from partforge.validate import fix_invoice, fix_mobile, validate_output_row


def test_placeholders():
    assert strip_placeholder("-- Unbranded --") is None
    assert strip_placeholder("-- No DIB Brand --") is None
    assert strip_placeholder("  ") is None
    assert strip_placeholder(None) is None
    assert strip_placeholder("Diablo") == "Diablo"


def test_supplier_code():
    assert strip_supplier_code("Freud Inc (2435)") == "Freud Inc"
    assert strip_supplier_code("Appliance Dealers Cooperative (APPDE)") == "Appliance Dealers Cooperative"


def test_fractions():
    assert dec_to_fraction(0.5) == "1/2"
    assert dec_to_fraction(50.25) == "50-1/4"
    assert dec_to_fraction("50-1/4") == "50-1/4"
    assert dec_to_fraction(0.045) == "3/64"
    assert dec_to_fraction(24.0) == "24"
    assert dec_to_fraction(0.875) == "7/8"
    assert dec_to_fraction(33.4375) == "33-7/16"


def test_units():
    assert normalize_unit("24", "in") == "24 in"
    assert normalize_unit("120", "V", invoice_style=True) == "120V"
    assert normalize_unit("47", "dBA") == "47 dBA"


def test_pack_count():
    assert parse_pack_count("Sanding Belt 6pc") == ("6", "pc")
    assert parse_pack_count("Cubitron II 50 Disc/Box") == ("50", "Box")


def test_classify_coarse_fallback():
    it, conf = extract_item_type('3M 775L Stikit Film P150 - Cubitron II 50 Disc/Box')
    assert it == "Sanding Disc" and conf >= 0.7
    cp, verified = classpath_for(it)
    assert verified and cp.endswith("Sanding Discs")
    cls = classify_row({"Part_Desc": '49-94-0013 Milw 5"x.045"x7/8" Metal Cut Off Disc'})
    assert cls["classpath"] == "Abrasives>Cutting & Grinding>Cut-Off Wheels & Discs"


def test_validators_and_fixes():
    issues = validate_output_row({"INVOICE_DESC": "x" * 41})
    assert any(i.code == "CHAR_LIMIT" for i in issues)
    assert fix_invoice("dishwasher leg 5 sst " + "x" * 60) == fix_invoice(
        fix_invoice("DISHWASHER LEG 5 SST " + "X" * 60))
    short = "Milwaukee Tool Milwaukee, Disc, X1"
    assert len(short) < 60
    # fix_mobile must never shrink below 60
    long_mobile = ", ".join(["a" * 30, "b" * 30, "c" * 30, "d" * 5])
    fixed = fix_mobile(long_mobile)
    assert len(fixed) <= 80
