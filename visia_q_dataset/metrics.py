from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
from loguru import logger
from scipy import stats
import typer

from visia_q_dataset.config import RAW_DATA_FILE, REPORTS_DIR
from visia_q_dataset.validation import validate_raw_dataset

app = typer.Typer()

GROUP_COL = "clinical_group"
OVIEDO_MAX_VALID = 2

INSTRUMENT_ITEMS: Dict[str, List[str]] = {
    "P-SIS": [f"paykel_{i}" for i in range(1, 6)],
    "MFQ": [f"mfq_{i}" for i in range(1, 34)],
    "SDQ": [f"sdq_{i}" for i in range(1, 26)],
    "EBIP": [f"ebip_{i}" for i in range(1, 15)],
    "ECIP": [f"ecip_{i}" for i in range(1, 23)],
    "PIUS-a": [f"eupi_{i}" for i in range(1, 12)],
}

SCORE_COLUMNS = {
    "P-SIS": "paykel_score",
    "MFQ": "mfq_score",
    "SDQ": "sdq_score",
    "EBIP": "ebip_score",
    "ECIP": "ecip_score",
    "PIUS-a": "eupi_score",
}

DISTRIBUTION_PROFILE = {
    "P-SIS": "Strictly non-normal. Scores are zero-inflated in controls and elevated in HR-G.",
    "MFQ": "Skewed. Negative skew in HR-G; positive skew in controls.",
    "SDQ": "Non-normal; multimodal distribution reflecting the three-group stratification.",
    "EBIP": "Zero-inflated. Most participants report low involvement with a long tail.",
    "ECIP": "Zero-inflated. Consistent with low baseline cyber-aggression rates.",
    "PIUS-a": "Right-skewed. Most adolescents show moderate use with a problematic subset.",
}

INSTRUMENT_DOMAIN = {
    "P-SIS": "Suicidality",
    "MFQ": "Depression",
    "SDQ": "General Behavior",
    "EBIP": "Bullying",
    "ECIP": "Cyberbullying",
    "PIUS-a": "Internet Use",
}


def _load_dataset(input_path: Path, skip_safeguard: bool) -> pd.DataFrame:
    if not skip_safeguard and not validate_raw_dataset(input_path):
        logger.error("Safeguard failed. Use --skip-safeguard to bypass validation.")
        raise typer.Exit(code=1)
    return pd.read_csv(input_path)


def _apply_quality_filters(df: pd.DataFrame) -> pd.DataFrame:
    filtered = df[(df["ov_score"] <= OVIEDO_MAX_VALID) & (df["maci_score_inval"] == 0)]
    return filtered


def calculate_cronbach_alpha(df: pd.DataFrame) -> float:
    df_items = df.select_dtypes(include=[np.number])
    item_variances = df_items.var(axis=0, ddof=1)
    total_score_var = df_items.sum(axis=1).var(ddof=1)
    n_items = df_items.shape[1]

    if n_items <= 1 or total_score_var == 0:
        return 0.0

    alpha = (n_items / (n_items - 1)) * (1 - (item_variances.sum() / total_score_var))
    return float(alpha)


def _shapiro_by_group(df: pd.DataFrame, score_col: str) -> List[Dict[str, object]]:
    results = []
    for group_value in sorted(df[GROUP_COL].dropna().unique()):
        group_data = df.loc[df[GROUP_COL] == group_value, score_col].dropna()
        if len(group_data) < 3:
            w_stat, p_val, is_normal = np.nan, np.nan, False
        else:
            try:
                w_stat, p_val = stats.shapiro(group_data)
            except Exception as exc:  # pragma: no cover - scipy edge cases
                logger.warning(f"Shapiro-Wilk failed for {score_col} in group {group_value}: {exc}")
                w_stat, p_val = np.nan, 0.0
            is_normal = p_val > 0.05

        results.append(
            {
                "score": score_col,
                "clinical_group": int(group_value),
                "n": int(len(group_data)),
                "shapiro_w": float(w_stat) if not np.isnan(w_stat) else np.nan,
                "shapiro_p": float(p_val) if not np.isnan(p_val) else np.nan,
                "is_normal": bool(is_normal),
            }
        )
    return results


@app.command()
def run_metrics(
    input_path: Path = RAW_DATA_FILE,
    output_dir: Path = REPORTS_DIR / "metrics",
    skip_safeguard: bool = typer.Option(False, help="Skip validation against the raw dataset."),
) -> None:
    df = _load_dataset(input_path, skip_safeguard)
    df = _apply_quality_filters(df)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Cronbach's alpha metrics
    alpha_rows = []
    for instrument, cols in INSTRUMENT_ITEMS.items():
        alpha = calculate_cronbach_alpha(df[cols])
        alpha_rows.append(
            {
                "instrument": instrument,
                "cronbach_alpha": round(alpha, 4),
                "n_items": len(cols),
                "n_rows": int(len(df)),
            }
        )

    alpha_df = pd.DataFrame(alpha_rows)
    alpha_path = output_dir / "cronbach_alpha.csv"
    alpha_df.to_csv(alpha_path, index=False)
    logger.success(f"Saved Cronbach alpha metrics to {alpha_path}")

    # Shapiro-Wilk per group
    shapiro_rows = []
    for instrument, score_col in SCORE_COLUMNS.items():
        shapiro_rows.extend(_shapiro_by_group(df, score_col))

    shapiro_df = pd.DataFrame(shapiro_rows)
    shapiro_path = output_dir / "shapiro_wilk_by_group.csv"
    shapiro_df.to_csv(shapiro_path, index=False)
    logger.success(f"Saved Shapiro-Wilk metrics to {shapiro_path}")

    # Summary table for distributional properties
    summary_rows = []
    for instrument, score_col in SCORE_COLUMNS.items():
        group_rows = shapiro_df[shapiro_df["score"] == score_col]
        any_non_normal = (group_rows["is_normal"] == False).any()  # noqa: E712
        all_non_normal = (group_rows["is_normal"] == False).all()  # noqa: E712
        if all_non_normal:
            shapiro_flag = "Yes (all groups)"
        elif any_non_normal:
            shapiro_flag = "Yes (some groups)"
        else:
            shapiro_flag = "No"

        summary_rows.append(
            {
                "instrument_domain": INSTRUMENT_DOMAIN[instrument],
                "instrument": instrument,
                "score_column": score_col,
                "shapiro_wilk_p_lt_0_05": shapiro_flag,
                "distribution_profile": DISTRIBUTION_PROFILE[instrument],
            }
        )

    summary_df = pd.DataFrame(summary_rows)
    summary_path = output_dir / "distributional_properties.csv"
    summary_df.to_csv(summary_path, index=False)
    logger.success(f"Saved distributional properties to {summary_path}")


if __name__ == "__main__":
    app()
