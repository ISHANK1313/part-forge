<div align="center">
  <h1>⚙️ PartForge</h1>
  <p><strong>AI Product Content Enrichment Pipeline</strong></p>

  <p>
    <a href="https://github.com/yourusername/partforge/actions"><img src="https://img.shields.io/badge/build-passing-brightgreen?style=for-the-badge" alt="Build Status"></a>
    <a href="https://github.com/yourusername/partforge/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue?style=for-the-badge" alt="License"></a>
    <a href="https://python.org"><img src="https://img.shields.io/badge/python-3.10+-blue.svg?style=for-the-badge&logo=python&logoColor=white" alt="Python"></a>
    <a href="https://streamlit.io"><img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white" alt="Streamlit"></a>
  </p>

  <p>
    <em>Raw industrial catalogue rows in → <strong>Unilog 252-column Delivery Format</strong> out.</em>
  </p>
</div>

---

## 📖 Overview

PartForge turns cryptic supplier rows like `49-94-0013 Milw 5"x.045"x7/8" Metal Cut Off Disc` into complete, standardised, search-ready product records:

*   ✨ **Canonical manufacturer/brand** (distributor ≠ manufacturer!)
*   🗂️ **Classpath taxonomy**
*   📝 **Six differently-formatted descriptions**
*   🏷️ **Attribute triplets**
*   🖼️ **Digital-asset references & packaging data**

It includes per-row confidence flags so **blank + flagged always beats invented** (hallucination control by design).

---

## 🚀 Quickstart

Get up and running with just 3 commands:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the pipeline
python main.py --input sample_input.csv --out out/

# 3. Run rule-compliance tests
python -m pytest tests -q
```

> [!TIP]
> **Optional:** Add a Gemini key in `.env` (`GEMINI_API_KEY=...`) to enable LLM enrichment. Without a key, the pipeline runs in a fully deterministic mode.

**Demo UI:**

```bash
streamlit run app.py
```

---

## 🛠️ Built With (Technologies Used)

PartForge leverages a modern, robust tech stack for data processing and AI enrichment:

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white" alt="Pandas"/>
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Streamlit"/>
  <img src="https://img.shields.io/badge/Gemini_API-4285F4?style=for-the-badge&logo=google&logoColor=white" alt="Google Gemini API"/>
  <img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite"/>
  <img src="https://img.shields.io/badge/Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white" alt="Pytest"/>
</p>

*   🐍 **Python 3**: Core backend programming language.
*   🐼 **Pandas**: Used for robust data manipulation, CSV parsing, and tabular DataFrame management.
*   👑 **Streamlit**: Powers the interactive web-based graphical user interface (GUI).
*   ⚡ **RapidFuzz**: Provides rapid fuzzy string matching used in supplier/brand identity resolution.
*   🧠 **Google Gemini API**: Utilized for precise JSON-mode LLM content enrichment (temperature 0).
*   💾 **SQLite**: Local caching engine to persist LLM calls, minimizing latency and API costs.
*   🧪 **Pytest**: Used for comprehensive rule-compliance validation and test assertions.
*   📊 **OpenPyXL**: Enables reading and writing to standard `.xlsx` spreadsheet formats.

---

## 🔄 Process Flow Diagram

Below is the execution pipeline for processing each row through PartForge (S0 to S9 steps). The deterministic spine ensures reliability, with LLM used optionally at the edges.

```mermaid
graph TD
    classDef primary fill:#4a90e2,stroke:#333,stroke-width:2px,color:#fff;
    classDef secondary fill:#f39c12,stroke:#333,stroke-width:2px,color:#fff;
    classDef endpoint fill:#2ecc71,stroke:#333,stroke-width:2px,color:#fff;
    classDef llm fill:#9b59b6,stroke:#333,stroke-width:2px,color:#fff;

    A([Raw Catalogue CSV]) --> B(S0: Cleanse):::primary
    B --> C(S1: Identity Vote):::primary
    C --> D(S2: Classify):::primary
    D --> E(S3: Attributes Extract):::primary
    E --> F(S5: Features/Extras):::primary
    F --> G(S4: Descriptions Compose):::primary
    G --> H(S6/S7: Assets & Packaging):::primary
    H --> I(S8: Validate):::primary
    I --> J(S9: Emit Output):::primary

    J --> K([Output Delivery Format Excel/CSV]):::endpoint
    J --> L([Audit Report Excel]):::endpoint

    E -.-> |Optional LLM Request| M{Gemini API}:::llm
    F -.-> |Optional LLM Request| M
    M -.-> E
    M -.-> F
```

---

## 🏗️ Architecture Diagram

The system architecture demonstrating how components and external integrations interact with the core engine:

```mermaid
flowchart TD
    classDef interface fill:#e74c3c,stroke:#333,stroke-width:2px,color:#fff;
    classDef engine fill:#34495e,stroke:#333,stroke-width:2px,color:#fff;
    classDef service fill:#8e44ad,stroke:#333,stroke-width:2px,color:#fff;
    classDef data fill:#16a085,stroke:#333,stroke-width:2px,color:#fff;

    subgraph Interfaces
        UI[Streamlit Web UI / app.py]:::interface
        CLI[Command Line Interface / main.py]:::interface
    end

    subgraph "PartForge Core Engine (src/partforge/)"
        Engine[Pipeline Executor]:::engine
        Modules[S0-S9 Process Modules]:::engine
        Engine <--> Modules
    end

    subgraph Services & Storage
        Cache[(SQLite Local Cache)]:::service
        Gemini[Google Gemini API]:::service
    end

    subgraph Data
        Input[(Raw CSV Inputs)]:::data
        Output[(Formatted Excel/CSV Outputs)]:::data
        Audit[(Audit Reports)]:::data
    end

    UI --> Engine
    CLI --> Engine
    Input --> Engine
    Engine --> Output
    Engine --> Audit
    Modules <--> Cache
    Modules <--> Gemini
```

---

## 💻 Proposed Solution UI (Wireframe)

A visual representation of the intuitive web interface provided by `app.py`:

```text
+-----------------------------------------------------------------------------------+
| ⚙️ PartForge — AI Product Content Enrichment                                      |
| Raw catalogue rows → Unilog 252-column Delivery Format. Deterministic rules...    |
+-----------------------------------------------------------------------------------+
| = Sidebar =       |  +---------------------------------------------------------+  |
| Run settings      |  | 📂 Upload input CSV                                     |  |
| [x] LLM (Gemini)  |  |    [ Drag and drop file here or Browse ]                |  |
|                   |  +---------------------------------------------------------+  |
| Parallel workers  |  | [ 🚀 Enrich ]                                           |  |
| [=======O-------] |  +---------------------------------------------------------+  |
| Row limit: [ 50]  |                                                               |
|                   |  [========================================] 100%              |
| Pipeline:         |  50/50 rows enriched                                          |
| S0 cleanse -> S1..|  rows/s: 2.5                                                  |
|                   |                                                               |
|                   |  [ ✔️ Done — 50 rows in 20s · 12 flagged NEEDS_REVIEW ]       |
|                   |                                                               |
|                   |  +-------------------------------------+ +-----------------+  |
|                   |  | Preview                             | | Downloads       |  |
|                   |  | +---------------------------------+ | | [⬇️ output.xlsx]|  |
|                   |  | | Mfg_Part | BRAND | Classpath ...| | | [⬇️ output.csv] |  |
|                   |  | | 49-94-00 | MILW  | Tools > ...  | | | [⬇️ audit.xlsx] |  |
|                   |  | | ...      | ...   | ...          | | |                 |  |
|                   |  | +---------------------------------+ | +-----------------+  |
|                   |  +-------------------------------------+                      |
+-----------------------------------------------------------------------------------+
```

---

## 📦 Outputs

The pipeline produces structured, reviewable data:

| File | Content |
|---|---|
| 📄 `out/output.xlsx` / `output.csv` | Exact 252-header Delivery Format, one row per input row |
| 📊 `out/audit_report.xlsx` | `NEEDS_REVIEW` flags, reason codes, confidence scores, and signals |
| 📈 `out/metrics.md` | PRD §5 metric table (run `python -m src.partforge.score --out out/`) |

---

## 🧠 How it works (The Spine)

Deterministic spine, LLM at the edges:

1. **`S0 cleanse`** — placeholders → `NULL`, distributor codes stripped, dedupe flagged
2. **`S1 identity vote`** — description tokens > MPN prefixes > supplier fuzzy (rapidfuzz)
3. **`S2 classify`** — keyword item-type → taxonomy classpath
4. **`S3 attributes`** — regex unit parser first; LLM fills only evidenced labels
5. **`S5 features/extras`** — series detection + one constrained LLM call per row
6. **`S4 descriptions`** — deterministic template composer (`INVOICE` ≤40 CAPS, `MOBILE` 60–80…)
7. **`S6/S7 assets & packaging`** — constructed filename/URL patterns, pack-count parsing
8. **`S8 validate`** — char limits, casing, UOM whitelist; auto-fix; flag what remains
9. **`S9 emit`** — header equality asserted against the bundled 252-column contract

*LLM calls are JSON-mode, temperature 0, SQLite-cached (`.cache/`), and parallelised (provider latency measured ~42 s/call regardless of model).*

---

## 📏 Design Rules (Abridged)

To maintain extreme quality, PartForge adheres to strict formatting standards:

*   ✔️ **Approved UOM abbreviations only** (`24 in`, `47 dBA`, never `24in`)
*   ✔️ **Decimals → trade inch fractions** (`50.25` → `50-1/4`; kerfs to 64ths)
*   ✔️ **Brand names match approved masters exactly**, ®/™ preserved
*   ✔️ **Headers are immutable**; passthrough columns copied verbatim
*   ✔️ **Every generated cell is auditable**: method + confidence + reason codes

---

## 📜 License

This project is licensed under the **MIT License**.
