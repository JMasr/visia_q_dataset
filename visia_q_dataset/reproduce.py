"""Reproduce and verify all numerical values reported in the paper.

Run with:
    python -m visia_q_dataset.reproduce
    make reproduce
"""
from pathlib import Path

import pandas as pd
from loguru import logger
from scipy import stats
import typer

from visia_q_dataset.config import RAW_DATA_FILE
from visia_q_dataset.metrics import INSTRUMENT_ITEMS, SCORE_COLUMNS, calculate_cronbach_alpha
from visia_q_dataset.validation import validate_raw_dataset

app = typer.Typer(add_completion=False)

# ── Ground-truth values from the published paper ──────────────────────────────

_PAPER_DEMOGRAPHICS = {
    1: {"name": "HR-G",  "N": 43,  "female": 38, "pct_f": 88.37,
        "age_mean": 14.88, "age_std": 1.13, "prim": 3,  "sec": 34, "upper": 6},
    2: {"name": "PC-G",  "N": 55,  "female": 24, "pct_f": 43.64,
        "age_mean": 14.58, "age_std": 1.39, "prim": 4,  "sec": 45, "upper": 6},
    3: {"name": "GC-G",  "N": 109, "female": 60, "pct_f": 55.05,
        "age_mean": 14.25, "age_std": 1.32, "prim": 23, "sec": 82, "upper": 4},
}
_PAPER_TOTAL = {
    "N": 207, "female": 122, "pct_f": 58.94, "age_mean": 14.47, "age_std": 1.32,
    "prim_n": 30, "prim_pct": 14.49,
    "sec_n": 161, "sec_pct": 77.78,
    "upper_n": 16, "upper_pct": 7.73,
}
_PAPER_ALPHA = {
    "MFQ": 0.9633, "P-SIS": 0.9283, "SDQ": 0.8220,
    "ECIP": 0.9654, "EBIP": 0.8338, "PIUS-a": 0.8390,
}
_PAPER_SHAPIRO = {k: "Yes (All groups)" for k in SCORE_COLUMNS}


# ── Formatting helpers ────────────────────────────────────────────────────────

def _trunc(value: float, decimals: int) -> float:
    """Floor-truncate to `decimals` decimal places (matches paper's age formatting)."""
    factor = 10 ** decimals
    return int(value * factor) / factor


def _pct(value: float, decimals: int = 2) -> float:
    """Round a fraction to a percentage (matches paper's sex/education formatting)."""
    return round(value * 100, decimals)


# ── Verification helper ───────────────────────────────────────────────────────

def _verify(label: str, computed, expected, failures: list, fmt: str = "") -> None:
    match = computed == expected
    symbol = "✓" if match else "✗"
    display = format(computed, fmt) if fmt else str(computed)
    detail = "" if match else f"  ← expected {format(expected, fmt) if fmt else expected}"
    print(f"  {symbol}  {label}: {display}{detail}")
    if not match:
        failures.append(label)


# ── Main command ──────────────────────────────────────────────────────────────

@app.command()
def reproduce(
    input_path: Path = typer.Argument(RAW_DATA_FILE, help="Path to the raw CSV dataset."),
    skip_safeguard: bool = typer.Option(False, help="Skip shape/column validation."),
) -> None:
    """Reproduce all paper tables and verify they match the published values."""

    if not skip_safeguard and not validate_raw_dataset(input_path):
        logger.error("Dataset validation failed. Use --skip-safeguard to bypass.")
        raise typer.Exit(code=1)

    df = pd.read_csv(input_path)
    failures: list = []

    _sep = "─" * 68

    # ── TABLE 1: DEMOGRAPHICS ─────────────────────────────────────────────────
    print(f"\n{'═'*68}")
    print("  TABLE 1 — Demographic Characteristics  (Section: Methods)")
    print(f"{'═'*68}")

    for grp, paper in _PAPER_DEMOGRAPHICS.items():
        sub = df[df["clinical_group"] == grp]
        print(f"\n  {paper['name']} (N={len(sub)})")
        print(f"  {_sep}")
        _verify("  N", len(sub), paper["N"], failures)
        _verify("  Sex — female count", int(sub["female"].sum()), paper["female"], failures)
        _verify("  Sex — female %",   _pct(sub["female"].mean()),  paper["pct_f"],  failures)
        _verify("  Age — mean (trunc)", _trunc(sub["age"].mean(), 2),         paper["age_mean"], failures)
        _verify("  Age — std  (trunc)", _trunc(sub["age"].std(ddof=1), 2),    paper["age_std"],  failures)
        _verify("  Education — Primary",       int((sub["education"] == 1).sum()), paper["prim"],  failures)
        _verify("  Education — Secondary",     int((sub["education"] == 2).sum()), paper["sec"],   failures)
        _verify("  Education — Upper Sec.",    int((sub["education"] == 3).sum()), paper["upper"], failures)

    print(f"\n  Total (N={len(df)})")
    print(f"  {_sep}")
    p = _PAPER_TOTAL
    _verify("  N",                len(df),                            p["N"],         failures)
    _verify("  Sex — female count", int(df["female"].sum()),          p["female"],    failures)
    _verify("  Sex — female %",   _pct(df["female"].mean()),          p["pct_f"],     failures)
    _verify("  Age — mean (trunc)", _trunc(df["age"].mean(), 2),      p["age_mean"],  failures)
    _verify("  Age — std  (trunc)", _trunc(df["age"].std(ddof=1), 2), p["age_std"],   failures)
    _verify("  Education — Primary   (N)",   int((df["education"] == 1).sum()),     p["prim_n"],   failures)
    _verify("  Education — Primary   (%)",   round((df["education"] == 1).mean() * 100, 2), p["prim_pct"], failures)
    _verify("  Education — Secondary (N)",   int((df["education"] == 2).sum()),     p["sec_n"],    failures)
    _verify("  Education — Secondary (%)",   round((df["education"] == 2).mean() * 100, 2), p["sec_pct"],  failures)
    _verify("  Education — Upper Sec.(N)",   int((df["education"] == 3).sum()),     p["upper_n"],  failures)
    _verify("  Education — Upper Sec.(%)",   round((df["education"] == 3).mean() * 100, 2), p["upper_pct"], failures)

    # ── TABLE 3: CRONBACH'S ALPHA ─────────────────────────────────────────────
    print(f"\n{'═'*68}")
    print("  TABLE 3 — Internal Consistency (Cronbach's α, complete sample N=207)")
    print(f"{'═'*68}\n")

    for instrument, cols in INSTRUMENT_ITEMS.items():
        alpha = _trunc(calculate_cronbach_alpha(df[cols]), 4)
        _verify(f"  α  {instrument}", alpha, _PAPER_ALPHA[instrument], failures, fmt=".4f")

    # ── TABLE 4: SHAPIRO-WILK ─────────────────────────────────────────────────
    print(f"\n{'═'*68}")
    print("  TABLE 4 — Distributional Properties (Shapiro-Wilk, combined N=207)")
    print(f"{'═'*68}\n")

    for instrument, score_col in SCORE_COLUMNS.items():
        _, p_val = stats.shapiro(df[score_col].dropna())
        flag = "Yes (All groups)" if p_val < 0.05 else "No"
        _verify(f"  SW {instrument} (p={p_val:.2e})", flag, _PAPER_SHAPIRO[instrument], failures)

    # ── SUMMARY ───────────────────────────────────────────────────────────────
    print(f"\n{'═'*68}")
    if not failures:
        print("  ✓  ALL VALUES MATCH THE PAPER  (0 failures)")
    else:
        print(f"  ✗  {len(failures)} VALUE(S) DO NOT MATCH THE PAPER:")
        for f in failures:
            print(f"       • {f}")
    print(f"{'═'*68}\n")

    raise typer.Exit(code=0 if not failures else 1)


if __name__ == "__main__":
    app()
