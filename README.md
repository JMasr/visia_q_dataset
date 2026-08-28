# visia_q_dataset

[![Python 3.10](https://img.shields.io/badge/python-3.10-blue)](https://www.python.org/downloads/release/python-3100/)
[![tests](https://github.com/JMasr/visia_q_dataset/actions/workflows/tests.yml/badge.svg)](https://github.com/JMasr/visia_q_dataset/actions/workflows/tests.yml)

Preprocessing, validation, and reproduction pipeline for the **VisIA-Q dataset** — a cross-sectional psychometric and demographic dataset of 207 adolescents at high-risk for suicide. Described in:

> Ramírez-Sánchez JM et al. "A cross-sectional psychometric and demographic dataset of adolescents at high-risk for suicide." *Scientific Data* (under major revision).

---

## How to use this repository

This guide walks you from a fresh clone to fully reproduced paper results in four steps.

### Step 1 — Set up the environment

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/) and Python 3.10.

```bash
git clone https://github.com/JMasr/visia_q_dataset
cd visia_q_dataset
make create_environment
make requirements
```

Expected output of `make requirements`: `uv sync` resolves dependencies and installs them into `.venv/`.

> All `make` commands call `.venv/bin/python` directly — you do **not** need to activate the virtual environment.

---

### Step 2 — Confirm the environment works

```bash
make test
```

Expected output: `29 passed` — unit tests run entirely on a synthetic dataset, no download needed. If this fails, the environment is not correctly set up.

---

### Step 3 — Download the dataset

The raw CSV contains clinical data from minors and requires a Data Use Agreement.

1. Request access at: **<https://doi.org/10.5281/zenodo.16600193>**
2. Once approved, download and place the file:

```bash
mkdir -p data/raw
# Download the file from the record reached via the DOI above, then place it at:
#   data/raw/visia_q_dataset.csv
```

Expected result: `data/raw/visia_q_dataset.csv` (207 rows × 145 columns, ~69 KB).

---

### Step 4 — Verify reproducibility

```bash
make reproduce
```

Expected output: `✓  ALL VALUES MATCH THE PAPER  (0 failures)`. Exit code 0 = all 167 checks pass.

This verifies, value by value, every number printed in the following tables of the Data Descriptor:

| Paper table | Content | Checks |
|---|---|---|
| Table 1 | Demographics per group and overall (N, sex, age, education level) | 35 |
| Table 3 | Cronbach's α per instrument | 6 |
| Table 4 | Distributional properties: Shapiro–Wilk normality outcome per instrument | 6 |
| Table 5 | Descriptive statistics per instrument per group (mean, SD, median, min, max) | 120 |

Two things in the paper are deliberately outside this check. Table 2 is the data dictionary, so it holds no computed values. The right-hand column of Table 4 is a prose description of each distribution's shape, not a statistic; only the normality outcome in that table is verified. Figure 1 is regenerated separately with `python -m visia_q_dataset.plots clinical-group-distribution`.

---

## What you can do next

Once the environment is set up and the dataset is in place, the following `make` commands are available:

| Command | What it does | Output |
|---|---|---|
| `make data_ov_maci_valid` | Apply both quality filters → **N=191** | `data/processed/visia_q_dataset_ov_maci_valid.csv` |
| `make data_ov_neg` | Oviedo filter only (ov_score ≤ 2) → N=203 | `data/processed/visia_q_dataset_ov_neg.csv` |
| `make data_maci_valid` | MACI validity filter only → N=195 | `data/processed/visia_q_dataset_maci_valid.csv` |
| `make metrics` | Cronbach α + Shapiro-Wilk per instrument | `reports/metrics/` |
| `make stats` | Descriptive statistics per instrument per group | `reports/metrics/descriptive_stats.csv` |
| `make reproduce` | Verify all paper values against raw data | Console output, exit 0/1 |
| `make uuid-audit` | Verify released participant IDs cannot be recomputed from public info | Console output, exit 0/1 |
| `make test` | Unit tests (no dataset needed) | `29 passed` |
| `make test-integration` | Integration tests (dataset required) | `4 passed` |

> Run `make help` to see all available commands.

The recommended quality filter for analysis is `make data_ov_maci_valid`, which retains participants where responses are genuine (Oviedo Infrequency Scale negative, `ov_score ≤ 2`) and the MACI-II validity indicator passes (`maci_score_inval = 0`). Post-filter breakdown: HR-G = 39, PC-G = 49, GC-G = 103.

---

## Participant identifiers

The `uuid` column holds RFC 4122 version-5 (name-based) UUIDs derived from each
participant's internal sequential study code under a namespace that is private to
the project and is not published. No direct or indirect participant identifier
enters the derivation, and the code-to-identity mapping never left the case report
form held at the recruiting hospitals.

Because a version-5 UUID is deterministic, the scheme's protection rests entirely
on the namespace staying secret. `make uuid-audit` tests that claim the way an
outsider would: it sweeps 21 candidate namespaces — the five standard RFC 4122 ones
plus sixteen derived from project- and institution-related strings — crossed with
the study-code patterns of both recruitment sites, and reports whether any of the
2,730,000 candidate derivations reproduces a released identifier.

```
Released identifiers : 207
Namespaces swept     : 21
Candidates tried     : 2,730,000
Matches              : 0
```

The unit tests for this audit include a positive control: an identifier minted
under a public namespace must be detected, so that a zero-match result on the real
data is evidence rather than an artefact of a broken search.

---

## Codebook

`data/codebook.csv` documents all 145 variables. Each row contains: `variable`, `instrument`, `domain`, `item_number`, `item_text_es` (Spanish original), `item_text_en` (English translation), `data_type`, `description`, `range_or_values`, `notes`.

---

## Citation

If you use this dataset or pipeline, please cite:

```
Ramírez-Sánchez JM et al. (2025). A cross-sectional psychometric and demographic
dataset of adolescents at high-risk for suicide. Scientific Data.
https://doi.org/10.5281/zenodo.16600193
```

---

## Project layout

```
├── Makefile
├── data/
│   ├── codebook.csv             <- Variable codebook (145 columns, ES + EN item texts)
│   ├── visia_q_structure.json   <- Instrument structure (used by make codebook)
│   ├── raw/                     <- visia_q_dataset.csv  [download from Zenodo; gitignored]
│   └── processed/               <- Filtered outputs     [generated by make data_*; gitignored]
├── reports/
│   └── metrics/                 <- Generated by make metrics / make stats (gitignored)
├── tests/
│   ├── conftest.py              <- Synthetic 10-row fixture for unit tests
│   ├── test_data.py             <- Filter and validation tests
│   └── test_codebook.py         <- Codebook pipeline tests
└── visia_q_dataset/
    ├── config.py                <- Paths
    ├── codebook.py              <- Build codebook from visia_q_structure.json
    ├── dataset.py               <- Quality filter commands
    ├── metrics.py               <- Cronbach α, Shapiro-Wilk, descriptive stats
    ├── plots.py                 <- Clinical group distribution figure
    ├── reproduce.py             <- Paper value verification
    └── validation.py            <- Schema check (207 rows × 145 columns)
```
