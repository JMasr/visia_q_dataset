from pathlib import Path

from loguru import logger
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import typer

from visia_q_dataset.config import FIGURES_DIR, RAW_DATA_FILE
from visia_q_dataset.validation import validate_raw_dataset

app = typer.Typer()

# Validity indicators, not psychometric constructs: they are excluded from the
# floor-effect figure because a zero on them carries no clinical meaning.
VALIDITY_SCORES = ("ov_score", "maci_score_inval", "maci_score_incons")

# (clinical_group code, legend label, bar colour) — plotted bottom-to-top within
# each variable, matching Figure 1 of the Data Descriptor.
FLOOR_EFFECT_GROUPS = (
    (1, "Target (High-Risk)", "#e65a76"),
    (2, "Confounder (Psychiatric)", "#ffbf4c"),
    (3, "Normative (Control)", "#7995e9"),
)

# Variables are ranked by the zero rate of the general control group, which is
# the reference for what counts as a floor effect in a normative population.
FLOOR_EFFECT_REFERENCE_GROUP = 3


def _load_dataset(input_path: Path, skip_safeguard: bool) -> pd.DataFrame:
    if not skip_safeguard and not validate_raw_dataset(input_path):
        logger.error("Safeguard failed. Use --skip-safeguard to bypass validation.")
        raise typer.Exit(code=1)
    return pd.read_csv(input_path)


@app.command()
def clinical_group_distribution(
    input_path: Path = RAW_DATA_FILE,
    output_path: Path = FIGURES_DIR / "clinical_group_distribution.png",
    skip_safeguard: bool = typer.Option(False, help="Skip validation against the raw dataset."),
) -> None:
    df = _load_dataset(input_path, skip_safeguard)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    group_labels = {1: "HR-G", 2: "PC-G", 3: "GC-G"}
    variables = ["female", "age", "education"]

    for ax, var in zip(axes, variables):
        counts = df.groupby([var, "clinical_group"]).size().unstack(fill_value=0)
        counts = counts.rename(columns=group_labels).sort_index()
        counts.plot(kind="bar", ax=ax)
        ax.set_title(f"clinical_group by {var}")
        ax.set_xlabel(var)
        ax.set_ylabel("count")
        ax.legend(title="clinical_group")

    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
    logger.success(f"Saved clinical group distribution plot to {output_path}")


def zero_score_rates(df: pd.DataFrame) -> pd.DataFrame:
    """Percentage of exact-zero scores per aggregated score column and clinical group.

    Returns one row per score column and one column per group label, ordered
    descending by the reference (general control) group.
    """
    score_columns = [
        column for column in df.columns if "score" in column and column not in VALIDITY_SCORES
    ]

    rates = pd.DataFrame(index=pd.Index(score_columns, name="variable"))
    for group_value, label, _ in FLOOR_EFFECT_GROUPS:
        group_df = df.loc[df["clinical_group"] == group_value, score_columns]
        # A participant whose MACI-II protocol could not be scored has no value
        # to compare against zero, so they leave the denominator rather than
        # counting as a non-zero score.
        rates[label] = group_df.eq(0).sum().div(group_df.notna().sum()).mul(100.0)

    reference_label = next(
        label
        for group_value, label, _ in FLOOR_EFFECT_GROUPS
        if group_value == FLOOR_EFFECT_REFERENCE_GROUP
    )
    return rates.sort_values(reference_label, ascending=False, kind="stable")


@app.command()
def floor_effects(
    input_path: Path = RAW_DATA_FILE,
    output_path: Path = FIGURES_DIR / "04_floor_effects.png",
    top: int = typer.Option(20, help="Number of score variables to display."),
    threshold: float = typer.Option(20.0, help="Floor-effect threshold, in percent."),
    table_path: Path = typer.Option(
        None, help="Optional CSV path for the plotted zero-rate values."
    ),
    skip_safeguard: bool = typer.Option(False, help="Skip validation against the raw dataset."),
) -> None:
    """Regenerate Figure 1: percentage of zero scores per instrument and group."""
    df = _load_dataset(input_path, skip_safeguard)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rates = zero_score_rates(df).head(top)

    fig, ax = plt.subplots(figsize=(18, 11))
    positions = np.arange(len(rates))
    bar_height = 0.27

    ax.axvline(
        threshold,
        color="#ff4c4c",
        linestyle="--",
        linewidth=3,
        label=f"Floor Effect Threshold ({threshold:.0f}%)",
    )
    for offset, (_, label, colour) in enumerate(FLOOR_EFFECT_GROUPS):
        ax.barh(
            positions + (offset - 1) * bar_height,
            rates[label].to_numpy(),
            height=bar_height,
            color=colour,
            label=label,
        )

    ax.set_yticks(positions)
    ax.set_yticklabels(rates.index)
    ax.set_xlabel("Percentage of Zero Scores (%)", fontsize=16, fontweight="bold")
    ax.tick_params(labelsize=14)
    ax.xaxis.grid(True, color="#d4d4d4", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(fontsize=14)

    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    logger.success(f"Saved floor-effect plot to {output_path}")

    if table_path is not None:
        table_path.parent.mkdir(parents=True, exist_ok=True)
        rates.round(2).to_csv(table_path)
        logger.success(f"Saved floor-effect values to {table_path}")


@app.command()
def main(
    input_path: Path = RAW_DATA_FILE,
    output_path: Path = FIGURES_DIR / "clinical_group_distribution.png",
    skip_safeguard: bool = typer.Option(False, help="Skip validation against the raw dataset."),
) -> None:
    clinical_group_distribution(
        input_path=input_path, output_path=output_path, skip_safeguard=skip_safeguard
    )


if __name__ == "__main__":
    app()
