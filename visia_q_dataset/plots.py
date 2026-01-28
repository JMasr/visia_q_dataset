from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from loguru import logger
import typer

from visia_q_dataset.config import FIGURES_DIR, RAW_DATA_FILE
from visia_q_dataset.validation import validate_raw_dataset

app = typer.Typer()


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
