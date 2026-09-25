"""Audit the released dataset against the instruments it claims to encode.

`make reproduce` checks that the paper's numbers follow from the data. This
checks that the data itself is internally coherent: that every item lives on its
instrument's response scale, that every aggregated score is recomputable from
its items, that the codebook describes what the file actually contains, and that
the psychometric structure behaves.

The batch-coding check is the one that matters most. A dataset assembled from
several collection batches can silently carry two different encodings of the
same answer; when the batches differ in composition, that shift is confounded
with group membership and inflates every reliability estimate. It is invisible
to a range check as long as both encodings happen to fit, so it is tested
directly.

Run with:
    python -m visia_q_dataset.audit
    make audit
"""

from pathlib import Path
import re
from typing import Dict, List

from loguru import logger
import pandas as pd
import typer

from visia_q_dataset.config import CODEBOOK_FILE, RAW_DATA_FILE
from visia_q_dataset.curate import MACI_SCALES, MACI_VERDICT
from visia_q_dataset.metrics import GROUP_COL, INSTRUMENT_ITEMS, SCORE_COLUMNS

app = typer.Typer(add_completion=False)

DASH = "–"  # the codebook writes ranges with an en dash

# Response scale each instrument's items are recorded on, per its manual.
ITEM_SCALES: Dict[str, tuple] = {
    "P-SIS": (0, 1),
    "MFQ": (0, 2),
    "SDQ": (0, 2),
    "EBIP": (0, 4),
    "ECIP": (0, 4),
    "PIUS-a": (0, 4),
}

# Theoretical range of each total score, from its item count and scale maximum.
SCORE_RANGES: Dict[str, tuple] = {
    "P-SIS": (0, 5),
    "MFQ": (0, 66),
    "SDQ": (0, 40),  # 20 items; the prosocial subscale is excluded
    "EBIP": (0, 56),
    "ECIP": (0, 88),
    "PIUS-a": (0, 44),
}

SDQ_SUBSCALES: Dict[str, List[int]] = {
    "sdq_score_ese": [3, 8, 13, 16, 24],
    "sdq_score_epc": [5, 7, 12, 18, 22],
    "sdq_score_eh": [2, 10, 15, 21, 25],
    "sdq_score_epr": [6, 11, 14, 19, 23],
    "sdq_score_epp": [1, 4, 9, 17, 20],
}
SDQ_DIFFICULTIES = ["sdq_score_ese", "sdq_score_epc", "sdq_score_eh", "sdq_score_epr"]

# Columns that are allowed to be empty, and why.
MISSING_ALLOWED = {column: "MACI-II protocol could not be scored" for column in MACI_SCALES}

EXPECTED_GRADIENT = [
    "paykel_score",
    "mfq_score",
    "sdq_score",
    "ebip_score",
    "ecip_score",
    "eupi_score",
]

CONVERGENT_PAIRS = [
    ("paykel_score", "maci_score_suicide", "P-SIS vs MACI-II suicide tendency"),
    ("mfq_score", "sdq_score_ese", "MFQ vs SDQ emotional symptoms"),
    ("mfq_score", "paykel_score", "depression vs suicidal ideation"),
]

ITEM_REST_FLOOR = 0.0

# An item-rest correlation says nothing about an item almost nobody endorsed:
# with a handful of positive answers its sign is noise. Such items are reported
# rather than failed.
MIN_ENDORSEMENTS_FOR_ITEM_REST = 5

# Below this total variation distance the two groups are the same distribution.
ENCODING_MATCH_TOLERANCE = 0.15


class Report:
    """Collects check outcomes and prints them like `make reproduce` does."""

    def __init__(self) -> None:
        self.failures: List[str] = []
        self.warnings: List[str] = []

    def section(self, title: str) -> None:
        print(f"\n{'=' * 72}\n  {title}\n{'=' * 72}\n")

    def check(self, label: str, ok: bool, detail: str = "") -> bool:
        print(f"  {'OK  ' if ok else 'FAIL'}  {label}{f': {detail}' if detail else ''}")
        if not ok:
            self.failures.append(f"{label}{f': {detail}' if detail else ''}")
        return ok

    def warn(self, label: str, detail: str = "") -> None:
        print(f"  NOTE  {label}{f': {detail}' if detail else ''}")
        self.warnings.append(f"{label}{f': {detail}' if detail else ''}")


def _items(df: pd.DataFrame, prefix: str, count: int) -> List[str]:
    return [f"{prefix}_{i}" for i in range(1, count + 1)]


_RANGE_RE = re.compile(rf"\s*(-?\d+)\s*[{DASH}-]\s*(-?\d+)\s*")


def _parse_range(text: object) -> tuple:
    """Parse '0-4', '0\u20134' or '-1\u201317' into a (low, high) pair."""
    if not isinstance(text, str):
        return ()
    match = _RANGE_RE.fullmatch(text)
    return (int(match.group(1)), int(match.group(2))) if match else ()


def _encoding_divergence(df: pd.DataFrame, columns: List[str], low: int):
    """How closely the records that never answer `low` match the rest, shifted.

    A second batch that wrote the "no" answer one step higher produces two
    groups whose response distributions are identical once one is shifted down
    by a single step. Severity alone does not do that: a participant who
    endorses every item concentrates on the extreme rather than reproducing the
    shape of everyone else's answers. Returns the total variation distance
    between the two, or None when every record uses `low`.
    """
    uses_min = (df[columns] == low).any(axis=1)
    if uses_min.all() or not uses_min.any():
        return None

    # On a two-level scale, shifting collapses every answer onto one value, so
    # a participant who endorses everything is indistinguishable from a second
    # encoding. The same holds when the avoiding group answers with a single
    # value. Neither case can be judged, so it is not reported as a failure.
    if df.loc[~uses_min, columns].stack().nunique() < 3:
        return None

    def histogram(frame: pd.DataFrame, offset: int) -> pd.Series:
        values = pd.Series(frame.to_numpy().ravel()).dropna() - offset
        return values.value_counts(normalize=True)

    baseline = histogram(df.loc[uses_min, columns], 0)
    shifted = histogram(df.loc[~uses_min, columns], 1)
    support = baseline.index.union(shifted.index)
    aligned_baseline = baseline.reindex(support, fill_value=0.0)
    aligned_shifted = shifted.reindex(support, fill_value=0.0)
    return float((aligned_baseline - aligned_shifted).abs().sum() / 2)


def _item_rest(df: pd.DataFrame, columns: List[str]) -> pd.Series:
    # A constant item has no correlation with anything; skip it rather than let
    # numpy divide by a zero standard deviation.
    return pd.Series(
        {
            column: (
                float("nan")
                if df[column].nunique() < 2
                else df[column].corr(df[[c for c in columns if c != column]].sum(axis=1))
            )
            for column in columns
        }
    )


def audit_structure(df: pd.DataFrame, codebook: pd.DataFrame, report: Report) -> None:
    report.section("STRUCTURE")
    report.check("207 records x 145 variables", df.shape == (207, 145), str(df.shape))
    report.check("participant identifiers are unique", df["uuid"].nunique() == len(df))
    report.check("no duplicated records", not df.drop(columns="uuid").duplicated().any())

    documented = set(codebook["variable"])
    undocumented = [c for c in df.columns if c not in documented]
    orphaned = [v for v in documented if v not in df.columns]
    report.check(
        "every column has a codebook entry",
        not undocumented,
        f"undocumented: {undocumented}" if undocumented else f"{len(df.columns)} columns",
    )
    report.check(
        "every codebook entry has a column",
        not orphaned,
        f"without a column: {orphaned}" if orphaned else f"{len(documented)} entries",
    )


def audit_missing(df: pd.DataFrame, report: Report) -> None:
    report.section("MISSING VALUES")
    unexpected = {
        column: int(df[column].isna().sum())
        for column in df.columns
        if column not in MISSING_ALLOWED and df[column].isna().any()
    }
    report.check(
        "missing values only where documented",
        not unexpected,
        f"unexpected: {unexpected}" if unexpected else "",
    )

    if df[MACI_SCALES].isna().any().any():
        incomplete = df[MACI_SCALES].isna().any(axis=1) & df[MACI_SCALES].notna().any(axis=1)
        report.check(
            "an unscored MACI-II profile is blanked in full",
            not incomplete.any(),
            f"partially blanked rows: {list(df.index[incomplete])}" if incomplete.any() else "",
        )
        blanked = df[MACI_SCALES].isna().all(axis=1)
        report.check(
            "every blanked MACI-II profile is flagged invalid",
            bool((df.loc[blanked, MACI_VERDICT] == 1).all()),
        )
        print(f"        {int(blanked.sum())} participant(s) without a scorable MACI-II profile")


def audit_coding(df: pd.DataFrame, report: Report) -> None:
    report.section("RESPONSE CODING")
    for instrument, columns in INSTRUMENT_ITEMS.items():
        low, high = ITEM_SCALES[instrument]
        observed = (int(df[columns].min().min()), int(df[columns].max().max()))
        report.check(
            f"{instrument}: items on the {low}{DASH}{high} response scale",
            low <= observed[0] and observed[1] <= high,
            f"observed {observed[0]}{DASH}{observed[1]}",
        )

    print()
    for instrument, columns in INSTRUMENT_ITEMS.items():
        low, high = ITEM_SCALES[instrument]
        if high - low < 2:
            report.check(
                f"{instrument}: single response encoding", True, "not testable on a binary scale"
            )
            continue
        divergence = _encoding_divergence(df, columns, low)
        if divergence is None:
            detail = ""
        elif divergence > ENCODING_MATCH_TOLERANCE:
            detail = (
                f"records that never answer {low} are not a shifted copy of the rest "
                f"(total variation {divergence:.3f} > {ENCODING_MATCH_TOLERANCE})"
            )
        else:
            detail = (
                f"records that never answer {low} are a shifted copy of the rest "
                f"(total variation {divergence:.3f} <= {ENCODING_MATCH_TOLERANCE}): "
                "two encodings of the same scale"
            )
        report.check(
            f"{instrument}: single response encoding",
            divergence is None or divergence > ENCODING_MATCH_TOLERANCE,
            detail,
        )

    print()
    constant = [c for cols in INSTRUMENT_ITEMS.values() for c in cols if df[c].nunique() == 1]
    if constant:
        report.warn("items with no variance", f"{constant} (no participant endorsed them)")
    else:
        print("  NOTE  every item shows variance")


def audit_scores(df: pd.DataFrame, report: Report) -> None:
    report.section("SCORE REPRODUCIBILITY")
    for instrument, columns in INSTRUMENT_ITEMS.items():
        score = SCORE_COLUMNS[instrument]
        if instrument == "SDQ":
            continue
        matches = int((df[columns].sum(axis=1) == df[score]).sum())
        report.check(
            f"{score} is the sum of its items", matches == len(df), f"{matches}/{len(df)}"
        )

    print()
    for subscale, numbers in SDQ_SUBSCALES.items():
        columns = [f"sdq_{n}" for n in numbers]
        matches = int((df[columns].sum(axis=1) == df[subscale]).sum())
        report.check(
            f"{subscale} is the sum of its 5 items", matches == len(df), f"{matches}/{len(df)}"
        )
    total = df[SDQ_DIFFICULTIES].sum(axis=1)
    report.check(
        "sdq_score is the sum of the four difficulties subscales",
        bool((total == df["sdq_score"]).all()),
    )
    internalising = df[["sdq_score_ese", "sdq_score_epr"]].sum(axis=1)
    externalising = df[["sdq_score_epc", "sdq_score_eh"]].sum(axis=1)
    report.check(
        "sdq_score_pi is emotional + peer", bool((internalising == df["sdq_score_pi"]).all())
    )
    report.check(
        "sdq_score_pe is conduct + hyperactivity",
        bool((externalising == df["sdq_score_pe"]).all()),
    )

    print()
    for instrument, (low, high) in SCORE_RANGES.items():
        score = SCORE_COLUMNS[instrument]
        observed = (int(df[score].min()), int(df[score].max()))
        report.check(
            f"{score} within its theoretical {low}{DASH}{high}",
            low <= observed[0] and observed[1] <= high,
            f"observed {observed[0]}{DASH}{observed[1]}",
        )


def audit_codebook(df: pd.DataFrame, codebook: pd.DataFrame, report: Report) -> None:
    report.section("CODEBOOK AGAINST DATA")
    mismatched = []
    for _, row in codebook.iterrows():
        column = row["variable"]
        if column not in df.columns or not pd.api.types.is_numeric_dtype(df[column]):
            continue
        declared = _parse_range(row["range_or_values"])
        values = df[column].dropna()
        if not declared or values.empty:
            continue
        observed = (int(values.min()), int(values.max()))
        if observed != declared:
            mismatched.append(f"{column} says {declared} holds {observed}")
    report.check(
        "declared value ranges match the data",
        not mismatched,
        f"{len(mismatched)} mismatch(es): {mismatched[:5]}" if mismatched else "",
    )

    conflicting = []
    for _, row in codebook.iterrows():
        column = row["variable"]
        if column not in df.columns:
            continue
        description = str(row["description"])
        if "Likert" not in description:
            continue
        declared = _parse_range(description.split("Likert:")[-1].strip(" )"))
        values = df[column].dropna()
        if not declared or values.empty:
            continue
        if not (declared[0] <= values.min() and values.max() <= declared[1]):
            conflicting.append(f"{column} says Likert {declared} holds {int(values.max())}")
    report.check(
        "declared response scales match the data",
        not conflicting,
        f"{len(conflicting)} conflict(s): {conflicting[:5]}" if conflicting else "",
    )


def audit_psychometrics(df: pd.DataFrame, report: Report) -> None:
    report.section("PSYCHOMETRIC STRUCTURE")
    for instrument, columns in INSTRUMENT_ITEMS.items():
        if instrument == "SDQ":
            # The SDQ total covers difficulties only; prosocial items are
            # scored in the opposite direction and belong to their own subscale.
            columns = [f"sdq_{n}" for s in SDQ_DIFFICULTIES for n in SDQ_SUBSCALES[s]]
        low = ITEM_SCALES[instrument][0]
        endorsements = (df[columns] > low).sum()
        assessable = [c for c in columns if endorsements[c] >= MIN_ENDORSEMENTS_FOR_ITEM_REST]
        rare = [c for c in columns if c not in assessable]

        correlations = _item_rest(df, columns)[assessable]
        weakest = correlations.min()
        report.check(
            f"{instrument}: every item correlates positively with its scale",
            weakest > ITEM_REST_FLOOR,
            f"weakest {correlations.idxmin()} = {weakest:+.3f}",
        )
        if rare:
            detail = ", ".join(f"{c} ({endorsements[c]})" for c in rare)
            report.warn(f"{instrument}: items too rarely endorsed to assess", detail)

    print()
    for subscale, numbers in SDQ_SUBSCALES.items():
        columns = [f"sdq_{n}" for n in numbers]
        correlations = _item_rest(df, columns)
        report.check(
            f"{subscale}: reverse scoring applied consistently",
            correlations.min() > ITEM_REST_FLOOR,
            f"weakest {correlations.idxmin()} = {correlations.min():+.3f}",
        )


def audit_plausibility(df: pd.DataFrame, report: Report) -> None:
    report.section("CLINICAL PLAUSIBILITY")
    for score in EXPECTED_GRADIENT:
        medians = df.groupby(GROUP_COL)[score].median()
        report.check(
            f"{score}: HR-G >= PC-G >= GC-G",
            medians[1] >= medians[2] >= medians[3],
            f"{medians[1]:.1f} / {medians[2]:.1f} / {medians[3]:.1f}",
        )

    print()
    for left, right, label in CONVERGENT_PAIRS:
        rho = df[left].corr(df[right], method="spearman")
        report.check(f"{label} converge", rho > 0.3, f"rho = {rho:+.3f}")


@app.command()
def main(
    input_path: Path = typer.Option(RAW_DATA_FILE, "--input", help="Dataset to audit."),
    codebook_path: Path = typer.Option(
        CODEBOOK_FILE, "--codebook", help="Codebook to check against."
    ),
) -> None:
    if not input_path.exists():
        logger.error(f"Dataset not found at {input_path}")
        raise typer.Exit(code=1)

    df = pd.read_csv(input_path)
    codebook = pd.read_csv(codebook_path)
    report = Report()

    audit_structure(df, codebook, report)
    audit_missing(df, report)
    audit_coding(df, report)
    audit_scores(df, report)
    audit_codebook(df, codebook, report)
    audit_psychometrics(df, report)
    audit_plausibility(df, report)

    print(f"\n{'=' * 72}")
    if report.failures:
        print(f"  {len(report.failures)} CHECK(S) FAILED")
        for failure in report.failures:
            print(f"    - {failure}")
    else:
        print("  ALL CHECKS PASSED")
    if report.warnings:
        print(f"  {len(report.warnings)} informational note(s), not failures:")
        for warning in report.warnings:
            print(f"    - {warning}")
    print(f"{'=' * 72}\n")

    raise typer.Exit(code=1 if report.failures else 0)


if __name__ == "__main__":
    app()
