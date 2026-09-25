"""Produce the curated VisIA-Q dataset from the previously published file.

Two corrections, both found by the pre-publication audit (`make audit`):

1. **ECIP-Q response scale.** The published item columns carry the 1-based
   response index of the data-collection form instead of the instrument's 0--4
   scale: an endorsed answer is stored as 2--5 rather than 1--4. The two
   collection batches also encoded the "No" answer differently — one wrote it
   as 0, the other as its index, 1 — so a single rule recovers the instrument
   scale in both: 0 already means "No" and stays 0; any other value is the
   1-based index and loses one. `ecip_score` is then recomputed as the sum of
   its items so that items and score agree for every record.

2. **MACI-II unscored protocols.** Two participants completed the MACI-II but
   their protocol could not be scored; the transcription recorded this as -1.
   A sentinel adjacent to the valid range (the scales start at 0) enters any
   arithmetic silently, so it is replaced by an explicit missing value. The
   whole profile of an unscored participant is blanked, including scales that
   happen to hold a 0: a protocol that could not be scored on one scale was not
   scored on any. `maci_score_inval` keeps its verdict and documents the reason.

Run with:
    python -m visia_q_dataset.curate --input OLD.csv --output NEW.csv
    make curate INPUT=OLD.csv OUTPUT=NEW.csv
"""

from pathlib import Path
from typing import List, Tuple

from loguru import logger
import pandas as pd
import typer

from visia_q_dataset.validation import MACI_SCALE_COLUMNS, MACI_VERDICT_COLUMN

app = typer.Typer(add_completion=False)

ECIP_ITEMS: List[str] = [f"ecip_{i}" for i in range(1, 23)]
ECIP_SCORE = "ecip_score"

# Re-exported from the schema module, which is the canonical reference.
MACI_SCALES = MACI_SCALE_COLUMNS
MACI_VERDICT = MACI_VERDICT_COLUMN
MACI_UNSCORED_SENTINEL = -1


def decode_ecip_items(items: pd.DataFrame) -> pd.DataFrame:
    """Map the form's raw response index onto the ECIP-Q 0--4 scale.

    0 already encodes "No" in the batch that used a 0-based "No"; every other
    value is a 1-based index. `where` keeps the zeros and decrements the rest,
    which is correct for both batches without having to identify them.
    """
    return items.where(items == 0, items - 1)


def curate(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Return the curated dataset and a cell-level record of what changed."""
    out = df.copy()
    changes = []

    def record(index, column, before, after, rule):
        changes.append(
            {
                "uuid": df.at[index, "uuid"],
                "row": int(index),
                "column": column,
                "before": before,
                "after": after,
                "rule": rule,
            }
        )

    # ── 1. ECIP-Q item columns ────────────────────────────────────────────────
    decoded = decode_ecip_items(df[ECIP_ITEMS])
    for column in ECIP_ITEMS:
        differs = decoded[column] != df[column]
        for index in df.index[differs]:
            record(
                index,
                column,
                int(df.at[index, column]),
                int(decoded.at[index, column]),
                "ecip-decode",
            )
    out[ECIP_ITEMS] = decoded

    # ── 2. ECIP-Q total score ─────────────────────────────────────────────────
    recomputed = decoded.sum(axis=1)
    for index in df.index[recomputed != df[ECIP_SCORE]]:
        record(
            index,
            ECIP_SCORE,
            int(df.at[index, ECIP_SCORE]),
            int(recomputed.at[index]),
            "ecip-score-recompute",
        )
    out[ECIP_SCORE] = recomputed

    # ── 3. MACI-II unscored protocols ─────────────────────────────────────────
    unscored = (df[MACI_SCALES] == MACI_UNSCORED_SENTINEL).any(axis=1)
    for index in df.index[unscored]:
        for column in MACI_SCALES:
            record(index, column, int(df.at[index, column]), "", "maci-unscored")
    out.loc[unscored, MACI_SCALES] = pd.NA
    out[MACI_SCALES] = out[MACI_SCALES].astype("Int64")

    return out, pd.DataFrame(changes)


@app.command()
def main(
    input_path: Path = typer.Option(..., "--input", help="Previously published CSV."),
    output_path: Path = typer.Option(..., "--output", help="Curated CSV to write."),
    changelog_path: Path = typer.Option(
        None, "--changelog", help="Optional CSV recording every changed cell."
    ),
    expected_path: Path = typer.Option(
        None,
        "--expected",
        help="Released curated CSV to compare the output against, cell by cell.",
    ),
) -> None:
    df = pd.read_csv(input_path)
    curated, changes = curate(df)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    curated.to_csv(output_path, index=False)
    logger.success(f"Curated dataset written to {output_path}")

    if expected_path is not None:
        # Read both back from disk so that dtype handling is identical.
        expected = pd.read_csv(expected_path)
        rederived = pd.read_csv(output_path)
        if list(expected.columns) != list(rederived.columns) or expected.shape != rederived.shape:
            logger.error(
                f"Shape or columns differ: expected {expected.shape}, re-derived {rederived.shape}"
            )
            raise typer.Exit(code=1)
        differing = expected.compare(rederived)
        if not differing.empty:
            logger.error(f"{len(differing)} record(s) differ from {expected_path}:")
            logger.error(differing.head(20).to_string())
            raise typer.Exit(code=1)
        logger.success(
            f"Re-derived file matches {expected_path} in every one of "
            f"{expected.shape[0] * expected.shape[1]} cells"
        )

    by_rule = changes.groupby("rule").size().to_dict() if len(changes) else {}
    unscored = (
        changes.loc[changes["rule"] == "maci-unscored", "row"].nunique() if len(changes) else 0
    )
    breakdown = ", ".join(f"{rule}: {count}" for rule, count in by_rule.items())
    logger.info(f"Cells changed: {len(changes)} ({breakdown})")
    logger.info(f"Participants with an unscored MACI-II profile: {unscored}")

    if changelog_path is not None:
        changelog_path.parent.mkdir(parents=True, exist_ok=True)
        changes.to_csv(changelog_path, index=False)
        logger.success(f"Change log written to {changelog_path}")


if __name__ == "__main__":
    app()
