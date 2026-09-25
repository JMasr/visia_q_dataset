# visia_q_dataset

[![Python 3.10](https://img.shields.io/badge/python-3.10-blue)](https://www.python.org/downloads/release/python-3100/)
[![tests](https://github.com/JMasr/visia_q_dataset/actions/workflows/tests.yml/badge.svg)](https://github.com/JMasr/visia_q_dataset/actions/workflows/tests.yml)

Preprocessing, validation, and reproduction pipeline for the **VisIA-Q dataset** — a cross-sectional psychometric and demographic dataset of 207 adolescents at high-risk for suicide. Described in:

> Ramírez-Sánchez JM et al. "A cross-sectional psychometric and demographic dataset of adolescents at high-risk for suicide." *Scientific Data* (2026, in revision).

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

Expected output: `41 passed` — unit tests run entirely on synthetic fixtures, no download needed. If this fails, the environment is not correctly set up.

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

The file is complete except for the MACI-II scale scores of two participants
whose protocol could not be scored; those cells are empty and both records carry
`maci_score_inval = 1`. Every other variable is present for all 207 records.

---

### Step 4 — Verify reproducibility

```bash
make reproduce
```

Expected output: `✓  ALL VALUES MATCH THE PAPER  (0 failures)`. Exit code 0 = all 185 checks pass.

This verifies, value by value, every number printed in the following tables of the Data Descriptor:

| Paper table | Content | Checks |
|---|---|---|
| Table 1 | Demographics per group and overall (N, sex, age, education level) | 35 |
| Table 3 | Cronbach's α per instrument | 6 |
| Table 4 | Distributional properties: Shapiro–Wilk normality outcome per instrument (pooled sample, 6) and per instrument within each clinical group (footnote, 18) | 24 |
| Table 5 | Descriptive statistics per instrument per group (mean, SD, median, min, max) | 120 |

Two things in the paper are deliberately outside this check. Table 2 is the data dictionary, so it holds no computed values. The right-hand column of Table 4 is a prose description of each distribution's shape, not a statistic; only the normality outcomes in that table — pooled and per group — are verified.

Figure 1 (floor effects: percentage of zero scores per aggregated score and clinical group) is regenerated separately with:

```bash
make figure1
```

This writes `reports/figures/04_floor_effects.png` — the image used in the manuscript — plus `reports/metrics/floor_effects.csv` with the plotted values. The figure shows the twenty aggregated scores with the highest zero rate in the general control group, ranked by that rate, excluding the validity indicators (`ov_score`, `maci_score_inval`, `maci_score_incons`). A separate demographic bar plot, not used in the paper, is available as `make plot_demographics`.

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
| `make figure1` | Regenerate Figure 1 (floor effects) | `reports/figures/04_floor_effects.png` |
| `make plot_demographics` | Demographic bar plot (not used in the paper) | `reports/figures/clinical_group_distribution.png` |
| `make audit` | Check the dataset against the instruments it encodes | Console output, exit 0/1 |
| `make curate INPUT=old.csv OUTPUT=new.csv [EXPECTED=released.csv]` | Re-derive the curated file from an earlier release and, optionally, verify it cell by cell | `new.csv`, `new_changes.csv`, exit 0/1 |
| `make uuid-audit` | Verify released participant IDs cannot be recomputed from public info | Console output, exit 0/1 |
| `make test` | Unit tests (no dataset needed) | `41 passed` |
| `make test-integration` | Integration tests (dataset required) | `4 passed` |

> Run `make help` to see all available commands.

The recommended quality filter for analysis is `make data_ov_maci_valid`, which retains participants where responses are genuine (Oviedo Infrequency Scale negative, `ov_score ≤ 2`) and the MACI-II validity indicator passes (`maci_score_inval = 0`). Post-filter breakdown: HR-G = 39, PC-G = 49, GC-G = 103.

---

## Data quality audit

```bash
make audit
```

`make reproduce` checks that the paper's numbers follow from the data. `make
audit` checks the data itself: that every item lies on its instrument's response
scale, that each aggregated score is recomputable from its items, that the SDQ
subscale composition and reverse-scored items reproduce the published scoring
rules, that the codebook describes what the file actually contains, and that
item–rest correlations are positive throughout.

It also runs a batch-coding check. A dataset assembled from several collection
batches can carry two different encodings of the same answer; when the batches
differ in composition that shift is confounded with group membership and
inflates every reliability estimate. The check compares the response
distribution of the records that never use a scale's lowest value against the
rest, shifted down one step: two encodings of the same scale match almost
exactly, while genuinely severe respondents do not.

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

The dataset:

```
Ramírez-Sánchez JM et al. (2026). VisIA-Q: a cross-sectional psychometric and
demographic dataset of adolescents at high-risk for suicide [Data set]. Zenodo.
https://doi.org/10.5281/zenodo.16600193
```

The Data Descriptor:

```
Ramírez-Sánchez JM et al. (2026). A cross-sectional psychometric and demographic
dataset of adolescents at high-risk for suicide. Scientific Data (in revision).
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
│   ├── figures/                 <- Generated by make figure1 (gitignored)
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
    ├── audit.py                 <- Dataset coherence checks (make audit)
    ├── curate.py                <- Re-derive the curated file from an earlier release (make curate)
    ├── plots.py                 <- Figure 1 (floor effects) + demographic plot
    ├── reproduce.py             <- Paper value verification
    └── validation.py            <- Schema check (207 rows × 145 columns)
```
