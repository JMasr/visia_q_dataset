# visia_q_dataset

<a target="_blank" href="https://cookiecutter-data-science.drivendata.org/">
    <img src="https://img.shields.io/badge/CCDS-Project%20template-328F97?logo=cookiecutter" />
</a>

<a target="_blank" href="https://www.python.org/downloads/release/python-3100/">
    <img src=https://img.shields.io/badge/python-3.10-blue" />
</a>

Repository to preprocess the `visia-q_dataset.csv` dataset from the VisIA project, with
quality filters (Oviedo Infrequency and MACI-II) and basic analysis utilities.

## Getting Started

1) Clone the repository:

```bash
git clone <URL_DEL_REPO>
cd visia_q_dataset
```

2) Create the environment and install dependencies:

```bash
make create_environment
make requirements
```

3) Download the CSV from Zenodo and place it at `data/raw/visia-q_dataset.csv`:

```bash
mkdir -p data/raw
curl -L "<ZENODO_URL_DEL_CSV>" -o data/raw/visia-q_dataset.csv
```

4) Run the filters with Make:

```bash
make data_ov_maci_valid
make data_ov_neg
make data_maci_valid
```

## Usage

Commands are based on Typer and can be executed from the repository root.

Dataset filtering:

```bash
python -m visia_q_dataset.dataset filter-all-valid
python -m visia_q_dataset.dataset filter-oviedo-negative
python -m visia_q_dataset.dataset filter-maci-valid
```

Auxiliary plots:

```bash
python -m visia_q_dataset.plots clinical-group-distribution
```

All commands accept `--input-path`, `--output-path`, and `--skip-safeguard` (to bypass validation of the original dataset).

## Cite

If you use this dataset or code in academic work, please cite the associated data descriptor and the Zenodo record once available.

## Project Organization

```
├── LICENSE            <- Open-source license if one is chosen
├── Makefile           <- Makefile with convenience commands like `make data` or `make train`
├── README.md          <- The top-level README for developers using this project.
├── data
│   ├── processed      <- The final, canonical data sets for modeling.
│   └── raw            <- The original, immutable data dump.
│
├── pyproject.toml     <- Project configuration file with package metadata for 
│                         visia_q_dataset and configuration for tools like black
├── reports            <- Generated analysis as HTML, PDF, LaTeX, etc.
│   └── figures        <- Generated graphics and figures to be used in reporting
│
├── requirements.txt   <- The requirements file for reproducing the analysis environment, e.g.
│                         generated with `pip freeze > requirements.txt`
│
└── visia_q_dataset   <- Source code for use in this project.
    │
    ├── __init__.py             <- Makes visia_q_dataset a Python module
    │
    ├── config.py               <- Store useful variables and configuration
    │
    ├── dataset.py              <- Scripts to download or generate data
    │
    ├── validation.py           <- Scripts with safety checks for data
    │
    └── plots.py                <- Code to create visualizations
```

--------
