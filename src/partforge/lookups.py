"""Reference lookups: approved UOM set, brand master, aliases, taxonomy, doc types.

Embedded minimal vocabularies per memory.md Q-01 fallback. Extensible via
reference/brands_extra.csv overrides loaded at startup when present.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REFERENCE_DIR = PROJECT_ROOT / "reference"
CONFIG_DIR = PROJECT_ROOT / "config"

# R-UOM-01: approved abbreviations. raw token -> canonical display abbreviation.
APPROVED_UOM: dict[str, str] = {
    "in": "in", "inch": "in", "inches": "in", '"': "in",
    "ft": "ft", "feet": "ft", "foot": "ft",
    "mm": "mm", "cm": "cm", "m": "m",
    "v": "V", "volt": "V", "volts": "V",
    "a": "A", "amp": "A", "amps": "A",
    "w": "W", "watt": "W", "watts": "W",
    "kw": "kW", "hp": "hp",
    "dba": "dBA", "db": "dBA",
    "rpm": "rpm", "psi": "psi",
    "lb": "lb", "lbs": "lb", "pound": "lb", "pounds": "lb",
    "kg": "kg", "g": "g", "oz": "oz", "ounce": "oz",
    "gal": "gal", "gallon": "gal", "qt": "qt",
    "pc": "pc", "pcs": "pc", "piece": "pc", "pieces": "pc",
    "box": "Box", "pack": "Pack", "each": "EA", "ea": "EA",
}

# Measurement groups used to sanity-check UOM against value context.
DIMENSION_UOMS = {"in", "ft", "mm", "cm", "m"}
ELECTRICAL_UOMS = {"V", "A", "W", "kW", "hp"}

# Attribute label vocabulary (Title Case). LLM must pick from this list or
# propose labels strictly evidenced in row text (R-ATT-06).
ATTRIBUTE_LABELS = [
    "Series", "Model", "Color", "Material", "Finish", "Grit", "Grit Rating",
    "Disc Diameter", "Belt Width", "Belt Length", "Arbor Hole Size",
    "Maximum RPM", "Abrasive Material", "Backing Material", "Bond Type",
    "Application", "Suitable For", "Quantity Per Pack", "Number in Package",
    "Number of Wash Cycles", "Voltage Rating", "Amperage Rating", "Wattage",
    "Mounting Type", "Plug Type", "Sound Level", "Size", "Overall Height",
    "Overall Width", "Overall Depth", "Depth With Door Open",
    "Minimum Height", "Maximum Height", "Capacity", "Weight Capacity",
    "Cutting Edge Length", "Thickness", "Wire Diameter", "Blade Length",
    "Blade Type", "Shank Diameter", "Thread Size", "Connection Type",
    "Working Pressure", "Temperature Rating", "Certification",
]


@dataclass
class BrandEntry:
    manufacturer: str          # legal casing e.g. "Milwaukee Tool"
    brand: str                 # with ® / ™ where part of approved name
    aliases: list[str] = field(default_factory=list)
    mpn_prefixes: list[str] = field(default_factory=list)
    domain: str = ""           # official manufacturer domain for MFR URL


# Alias-token -> entry. Tokens are lowercase; brand word without marks included.
BRAND_MASTER: dict[str, BrandEntry] = {}
_ENTRIES = [
    BrandEntry("Milwaukee Tool", "Milwaukee®", ["milw", "milwaukee"], ["49-", "48-"], "milwaukeetool.com"),
    BrandEntry("Freud Inc", "Diablo®", ["diablo"], ["DCB", "DIA"], "freudtools.com"),
    BrandEntry("Freud Inc", "Freud®", ["freud"], ["LU", "TKR"], "freudtools.com"),
    BrandEntry("3M Company", "3M™", ["3m", "cubitron"], ["3MABR", "MM-"], "3m.com"),
    BrandEntry("Mirka Ltd", "Mirka®", ["mirka"], [], "mirka.com"),
    BrandEntry("Robert Bosch GmbH", "Bosch®", ["bosch"], ["2608"], "boschtools.com"),
    BrandEntry("Stanley Black & Decker", "DEWALT®", ["dewalt"], ["DWA", "DWHT", "DCD"], "dewalt.com"),
    BrandEntry("Makita Corporation", "Makita®", ["makita"], ["A-"], "makitatools.com"),
    BrandEntry("Norton Abrasives", "Norton®", ["norton"], ["662"], "nortonabrasives.com"),
    BrandEntry("Metabo Corporation", "Metabo®", ["metabo"], [], "metabo.com"),
    BrandEntry("Fein GmbH", "FEIN®", ["fein"], [], "fein.com"),
    BrandEntry("Whirlpool Corporation", "Whirlpool®", ["whirlpool"], ["WDTS", "WDF", "WDT"], "whirlpool.com"),
    BrandEntry("Rheem Manufacturing", "FRIGIDAIRE®", ["frigidaire"], ["PDSH", "FFID", "FFBD"], "frigidaire.com"),
    BrandEntry("Rheem Manufacturing", "Rheem®", ["rheem"], [], "rheem.com"),
    BrandEntry("KitchenAid", "KitchenAid®", ["kitchenaid"], ["KDTM", "KDTE"], "kitchenaid.com"),
    BrandEntry("Maytag Corporation", "Maytag®", ["maytag"], ["MDB"], "maytag.com"),
    BrandEntry("GE Appliances", "GE®", ["general electric"], ["GDT", "GDF", "GDP"], "geappliances.com"),
    BrandEntry("LG Electronics", "LG®", ["lg"], ["LDF", "LDP", "LDT"], "lg.com"),
    BrandEntry("Samsung Electronics", "Samsung®", ["samsung"], ["DW80"], "samsung.com"),
    BrandEntry("Electrolux", "Electrolux®", ["electrolux"], ["EIDW", "EI24"], "electrolux.com"),
    # observed in the 1000-row sample (decking / lighting / tools)
    BrandEntry("Trex Company", "Trex®", ["trex"], [], "trex.com"),
    BrandEntry("AZEK Building Products", "AZEK®", ["azek"], [], "azek.com"),
    BrandEntry("Kichler Lighting", "Kichler®", ["kichler"], [], "kichler.com"),
    BrandEntry("Festool GmbH", "Festool®", ["festool"], [], "festool.com"),
    BrandEntry("Kreg Tool Company", "Kreg®", ["kreg"], [], "kregtool.com"),
    BrandEntry("Grizzly Industrial", "Grizzly®", ["grizzly"], ["T"], "grizzly.com"),
]
for _e in _ENTRIES:
    for _token in [_e.brand.replace("®", "").replace("™", "").lower(), *_e.aliases]:
        BRAND_MASTER[_token.strip()] = _e

# Doc types for asset filename columns (R-AST-02) — fixed column names.
DOC_TYPES = [
    "Specification Sheet", "Owners/User Manual", "Instruction/Installation Manual",
    "SDS", "Catalog", "Service Manual", "Line Drawing", "RoHS",
    "Full Engineering Drawing", "Energy Star Guide", "Technical Bulletin",
    "Submittal", "Compatibility Chart", "Size Chart", "Product Label/Insert",
]

# Taxonomy: item-type keyword -> classpath (R-CLS-01, > joined, no spaces).
TAXONOMY: list[tuple[tuple[str, ...], str]] = [
    (("cut off disc", "cut-off disc", "cutoff disc", "cut off wheel", "cut-off wheel"), "Abrasives>Cutting & Grinding>Cut-Off Wheels & Discs"),
    (("grinding disc", "grinding wheel"), "Abrasives>Cutting & Grinding>Grinding Wheels"),
    (("flap disc",), "Abrasives>Sanding & Finishing>Flap Discs"),
    (("sanding belt", "sand belt", "abrasive belt"), "Abrasives>Sanding & Finishing>Sanding Belts"),
    (("sanding disc",), "Abrasives>Sanding & Finishing>Sanding Discs"),
    (("sandpaper", "sanding sheet", "abrasive sheet"), "Abrasives>Sanding & Finishing>Abrasive Sheets"),
    (("wire wheel", "wire brush"), "Abrasives>Brushes>Wire Brushes"),
    (("drill bit",), "Power Tool Accessories>Drilling>Drill Bits"),
    (("saw blade",), "Power Tool Accessories>Cutting>Saw Blades"),
    (("hole saw",), "Power Tool Accessories>Cutting>Hole Saws"),
    (("dishwasher",), "Appliances & Consumer Electronics>Kitchen Appliances>Built-In Dishwashers"),
    (("refrigerator", "fridge"), "Appliances & Consumer Electronics>Kitchen Appliances>Refrigerators"),
    (("microwave",), "Appliances & Consumer Electronics>Kitchen Appliances>Microwave Ovens"),
    (("range", "stove", "oven"), "Appliances & Consumer Electronics>Kitchen Appliances>Ranges & Ovens"),
    (("washing machine", "washer"), "Appliances & Consumer Electronics>Laundry>Washing Machines"),
    (("dryer",), "Appliances & Consumer Electronics>Laundry>Clothes Dryers"),
    (("pipe fitting", "fitting"), "Plumbing>Fittings>Pipe Fittings"),
    (("ball valve", "gate valve", "valve"), "Plumbing>Valves>General Purpose Valves"),
    (("hose",), "Plumbing>Tubing & Hose>Hoses"),
    (("glove",), "Safety>Hand Protection>Gloves"),
    (("helmet", "hard hat"), "Safety>Head Protection>Helmets"),
    (("safety glasses", "goggles"), "Safety>Eye Protection>Safety Glasses"),
    # coarse single-noun fallbacks LAST
    (("disc",), "Abrasives>Sanding & Finishing>Sanding Discs"),
    (("belt",), "Abrasives>Sanding & Finishing>Sanding Belts"),
    (("wheel",), "Abrasives>Cutting & Grinding>Grinding Wheels"),
    # observed sample categories (decking / lighting / tools)
    (("decking", "deck board"), "Building Materials>Decking>Composite Decking Boards"),
    (("fascia",), "Building Materials>Decking>Deck Fascia Boards"),
    (("baluster",), "Building Materials>Decking>Deck Balusters"),
    (("rail kit", "t-rail kit", "railing kit"), "Building Materials>Decking>Deck Railing Kits"),
    (("rail", "railing"), "Building Materials>Decking>Deck Railing"),
    (("fence", "gate"), "Building Materials>Fencing>Fence Panels & Gates"),
    (("chandelier",), "Lighting & Fans>Indoor Lighting>Chandeliers"),
    (("pendant",), "Lighting & Fans>Indoor Lighting>Pendant Lights"),
    (("ceiling fan",), "Lighting & Fans>Ceiling Fans>Ceiling Fans"),
    (("bulb", "led lamp", "incan"), "Lighting & Fans>Light Bulbs>LED Light Bulbs"),
    (("led",), "Lighting & Fans>Light Bulbs>LED Light Bulbs"),
    (("outlet", "receptacle"), "Electrical>Wiring Devices>Outlets & Receptacles"),
    (("sander",), "Power Tools>Sanders>Sanders"),
    (("torx", "drive bit", "power bit"), "Power Tool Accessories>Driving>Drive Bits"),
]


def load_extra_brands() -> None:
    """Merge reference/brands_extra.csv when the full brand master is supplied.

    Columns: manufacturer,brand,aliases(|-separated),mpn_prefixes(|-separated),domain
    """
    path = REFERENCE_DIR / "brands_extra.csv"
    if not path.exists():
        return
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            entry = BrandEntry(
                manufacturer=row["manufacturer"].strip(),
                brand=row["brand"].strip(),
                aliases=[a.strip().lower() for a in row.get("aliases", "").split("|") if a.strip()],
                mpn_prefixes=[p.strip() for p in row.get("mpn_prefixes", "").split("|") if p.strip()],
                domain=row.get("domain", "").strip(),
            )
            tokens = [entry.brand.replace("®", "").replace("™", "").lower(), *entry.aliases]
            for token in tokens:
                BRAND_MASTER[token.strip()] = entry


def lookup_brand(token: str) -> BrandEntry | None:
    return BRAND_MASTER.get(token.strip().lower())


def classpath_for(item_type: str) -> tuple[str, bool]:
    """Return (classpath, verified). First keyword hit wins."""
    t = item_type.lower()
    for keywords, cp in TAXONOMY:
        if any(k in t for k in keywords):
            return cp, True
    return "", False


def approved_uom(raw: str) -> str | None:
    """Map a raw unit string to its approved abbreviation, else None."""
    return APPROVED_UOM.get(raw.strip().strip(".").lower())
