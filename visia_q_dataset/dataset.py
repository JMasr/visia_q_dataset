from pathlib import Path

import pandas as pd
from loguru import logger
import typer

from visia_q_dataset.config import PROCESSED_DATA_DIR, RAW_DATA_FILE
from visia_q_dataset.validation import validate_raw_dataset

app = typer.Typer()

OVIEDO_NEGATIVE_MAX = 2


def _load_dataset(input_path: Path, skip_safeguard: bool) -> pd.DataFrame:
    if not skip_safeguard and not validate_raw_dataset(input_path):
        logger.error("Safeguard failed. Use --skip-safeguard to bypass validation.")
        raise typer.Exit(code=1)
    return pd.read_csv(input_path)


def _write_dataset(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    logger.success(f"Saved dataset to {output_path}")


@app.command()
def filter_all_valid(
    input_path: Path = RAW_DATA_FILE,
    output_path: Path = PROCESSED_DATA_DIR / "visia_q_dataset_ov_maci_valid.csv",
    skip_safeguard: bool = typer.Option(False, help="Skip validation against the raw dataset."),
) -> None:
    df = _load_dataset(input_path, skip_safeguard)
    filtered = df[(df["ov_score"] <= OVIEDO_NEGATIVE_MAX) & (df["maci_score_inval"] == 0)]
    logger.info(f"Rows kept: {len(filtered)} / {len(df)}")
    _write_dataset(filtered, output_path)


@app.command()
def filter_oviedo_negative(
    input_path: Path = RAW_DATA_FILE,
    output_path: Path = PROCESSED_DATA_DIR / "visia_q_dataset_ov_neg.csv",
    skip_safeguard: bool = typer.Option(False, help="Skip validation against the raw dataset."),
) -> None:
    df = _load_dataset(input_path, skip_safeguard)
    filtered = df[df["ov_score"] <= OVIEDO_NEGATIVE_MAX]
    logger.info(f"Rows kept: {len(filtered)} / {len(df)}")
    _write_dataset(filtered, output_path)


@app.command()
def filter_maci_valid(
    input_path: Path = RAW_DATA_FILE,
    output_path: Path = PROCESSED_DATA_DIR / "visia_q_dataset_maci_valid.csv",
    skip_safeguard: bool = typer.Option(False, help="Skip validation against the raw dataset."),
) -> None:
    df = _load_dataset(input_path, skip_safeguard)
    filtered = df[df["maci_score_inval"] == 0]
    logger.info(f"Rows kept: {len(filtered)} / {len(df)}")
    _write_dataset(filtered, output_path)


@app.command()
def main(
    input_path: Path = RAW_DATA_FILE,
    output_path: Path = PROCESSED_DATA_DIR / "visia_q_dataset_ov_maci_valid.csv",
    skip_safeguard: bool = typer.Option(False, help="Skip validation against the raw dataset."),
) -> None:
    filter_all_valid(
        input_path=input_path, output_path=output_path, skip_safeguard=skip_safeguard
    )


if __name__ == "__main__":
    app()
