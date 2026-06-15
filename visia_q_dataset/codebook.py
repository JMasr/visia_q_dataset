"""
Build the VisIA-Q codebook with Spanish (item_text_es) and English (item_text_en) item texts.

Three internal stages:
  1. extract_spanish_items  — parse visia_q_structure.json → items per instrument
  2. build_mapping          — map items to published column names → {variable: item_text_es}
  3. update_codebook        — apply mapping to codebook.csv, inserting both text columns
"""
import json
import re
from pathlib import Path

import pandas as pd
import typer
from loguru import logger

from visia_q_dataset.config import CODEBOOK_FILE, STRUCTURE_JSON

app = typer.Typer()

# ---------------------------------------------------------------------------
# Oviedo / notes skip and split patterns
# ---------------------------------------------------------------------------

_OVIEDO_SKIP = [
    re.compile(r"^O\d+\."),        # O6. O7. O8.  (ECIP prefix-style)
    re.compile(r"^\d+O[\s\.]"),    # 1O , 2O , 3O.  (SDQ / MFQ infix-style)
    re.compile(r"^xO\."),          # xO.  (PAYKEL auxiliary)
    re.compile(r"^Observaciones"), # free-text notes fields
]

# EUPI items 4 and 10 contain an embedded Oviedo check after a comma.
# Pattern matches ",9O " and ",AO " (and similar).
_EMBEDDED_OVIEDO_RE = re.compile(r",\s*(?:\d+|[A-Z])O\s")

# ---------------------------------------------------------------------------
# MACI-II hardcoded name → published column name
# (positional mapping is impossible because multiple entries share a leading digit)
# ---------------------------------------------------------------------------

MACI_NAME_TO_COLUMN: dict[str, str] = {
    "1 Introvertido":              "maci_score_intro",
    "2 Inhibido":                  "maci_score_inhi",
    "3 Sumiso":                    "maci_score_su",
    "4 Dramático":                 "maci_score_drama",
    "5 Egocéntrico":               "maci_score_ego",
    "6A Rebelde":                  "maci_score_rebel",
    "6B Hostil":                   "maci_score_hostil",
    "7 Conformista":               "maci_score_conform",
    "8A Resentido":                "maci_score_resent",
    "8B Agraviado":                "maci_score_ag",
    "9 Tendencia límite":          "maci_score_borderline",
    "FF Tendencia suicida":        "maci_score_suicide",
    "1 Invalidez":                 "maci_score_inval",
    "2 Inconsistencia":            "maci_score_incons",
    "2 Pensamientos suicidas":     "maci_score_suicide_thoughts",
    "3 Autolesiones no suicidas":  "maci_score_nssi",
}

# ---------------------------------------------------------------------------
# SDQ subscale score → published column name
# (ordered to match the columns_with_scores list in the JSON)
# ---------------------------------------------------------------------------

SDQ_SCORE_NAME_TO_COLUMN: dict[str, str] = {
    "Escala de problemas de conducta": "sdq_score_epc",
    "Escala de hiperactividad":        "sdq_score_eh",
    "Escala de síntomas emocionales":  "sdq_score_ese",
    "Escala de problemas de relación": "sdq_score_epr",
    "Escala de problemas prosociales": "sdq_score_epp",
    "Puntuación de internalización":   "sdq_score_pi",
    "Puntuación de externalización":   "sdq_score_pe",
    "PUNTUACIÓN TOTAL SDQ":            "sdq_score",
}

# ---------------------------------------------------------------------------
# Positional mapping: instrument key → (column prefix, expected count in published CSV)
# ---------------------------------------------------------------------------

POSITIONAL_INSTRUMENTS: dict[str, tuple[str, int]] = {
    "EBIP":   ("ebip",    14),  # JSON has 13 items; ebip_14 flagged as MANUAL_REVIEW
    "ECIP":   ("ecip",    22),
    "EUPI":   ("eupi",    11),  # items 4 and 10 include embedded Oviedo (stripped)
    "MFQ":    ("mfq",     33),
    "PAYKEL": ("paykel",   5),
    "SDQ":    ("sdq",     25),
}

# Target column order after update
_COLUMN_ORDER = [
    "variable", "instrument", "domain", "item_number",
    "item_text_es", "item_text_en",
    "data_type", "description", "range_or_values", "notes",
]


# ===========================================================================
# Stage 1 — extract
# ===========================================================================

def _is_skip(text: str) -> bool:
    return any(pat.match(text) for pat in _OVIEDO_SKIP)


def _strip_embedded_oviedo(text: str) -> str:
    m = _EMBEDDED_OVIEDO_RE.search(text)
    return text[: m.start()].strip() if m else text


def extract_spanish_items(json_path: Path) -> tuple[dict, dict]:
    """
    Parse visia_q_structure.json and extract Spanish item texts per instrument.

    Returns:
        items_by_instrument: {instrument_key: [cleaned_text, ...]} in JSON list order,
            with Oviedo/notes entries removed and embedded Oviedo text stripped.
        structure: the raw parsed JSON dict (needed by build_mapping for score columns).
    """
    with open(json_path, encoding="utf-8") as fh:
        structure = json.load(fh)

    items_by_instrument: dict = {}
    for key, data in structure["VISIA_Q"].items():
        cleaned = []
        for text in data.get("columns_with_items", []):
            if _is_skip(text):
                continue
            cleaned.append(_strip_embedded_oviedo(text))
        items_by_instrument[key] = cleaned
        logger.debug(f"{key}: {len(cleaned)} items extracted")

    return items_by_instrument, structure


# ===========================================================================
# Stage 2 — map
# ===========================================================================

def build_mapping(items_by_instrument: dict, structure: dict) -> dict:
    """
    Map extracted Spanish item texts to published column names.

    Returns:
        {variable_name: item_text_es}
    """
    mapping: dict = {}

    # --- Positional mapping for item-level instruments ---
    for instr_key, (prefix, n_published) in POSITIONAL_INSTRUMENTS.items():
        items = items_by_instrument.get(instr_key, [])
        n_json = len(items)
        for idx, text in enumerate(items):
            mapping[f"{prefix}_{idx + 1}"] = text
        if n_json < n_published:
            for col_num in range(n_json + 1, n_published + 1):
                mapping[f"{prefix}_{col_num}"] = "MANUAL_REVIEW"
            logger.warning(
                f"{instr_key}: JSON has {n_json} items but published dataset has "
                f"{n_published}. Column(s) {n_json + 1}–{n_published} flagged as MANUAL_REVIEW."
            )

    # --- MACI-II: name-based from columns_with_items ---
    for text in items_by_instrument.get("MACI-II", []):
        col = MACI_NAME_TO_COLUMN.get(text)
        if col:
            mapping[col] = text
        else:
            logger.warning(f"MACI-II: no mapping found for '{text}'")

    # --- MACI-II: also map FF Tendencia suicida from columns_with_scores ---
    for score_text in structure["VISIA_Q"].get("MACI-II", {}).get("columns_with_scores", []):
        col = MACI_NAME_TO_COLUMN.get(score_text)
        if col:
            mapping[col] = score_text

    # --- SDQ: subscale scores from columns_with_scores ---
    for score_text in structure["VISIA_Q"].get("SDQ", {}).get("columns_with_scores", []):
        col = SDQ_SCORE_NAME_TO_COLUMN.get(score_text)
        if col:
            mapping[col] = score_text

    logger.info(f"build_mapping: {len(mapping)} variables mapped")
    return mapping


# ===========================================================================
# Stage 3 — update
# ===========================================================================

def update_codebook(
    codebook_path: Path,
    mapping: dict,
    save_intermediates: bool = False,
) -> None:
    """
    Add item_text_es and item_text_en columns to codebook.csv (in-place).

    - item_text_es: Spanish original text from visia_q_structure.json.
    - item_text_en: empty stub — user fills in from official English instrument manuals.
    - The existing empty 'item_text' column is renamed to 'item_text_en'.
    """
    df = pd.read_csv(codebook_path, keep_default_na=False)

    # Rename existing item_text → item_text_en (preserving empty values as stubs)
    if "item_text" in df.columns and "item_text_en" not in df.columns:
        df = df.rename(columns={"item_text": "item_text_en"})

    # Populate item_text_es from mapping; empty string for unmapped rows
    df["item_text_es"] = df["variable"].map(mapping).fillna("").astype(str)

    # Reorder to canonical layout
    df = df.reindex(columns=_COLUMN_ORDER)

    n_mapped = (df["item_text_es"] != "").sum()
    n_manual = (df["item_text_es"] == "MANUAL_REVIEW").sum()
    n_empty = (df["item_text_es"] == "").sum()
    logger.info(
        f"update_codebook: {n_mapped} rows populated "
        f"({n_manual} MANUAL_REVIEW, {n_empty} empty — scores/demographics)."
    )

    if save_intermediates:
        debug_path = codebook_path.parent / "codebook_mapping_debug.csv"
        pd.DataFrame(
            [{"variable": k, "item_text_es": v} for k, v in mapping.items()]
        ).to_csv(debug_path, index=False)
        logger.info(f"Intermediate mapping saved to {debug_path}")

    df.to_csv(codebook_path, index=False)
    logger.success(f"Codebook updated: {codebook_path}")


# ===========================================================================
# CLI
# ===========================================================================

@app.command()
def build(
    json_path: Path = typer.Option(STRUCTURE_JSON, help="Path to visia_q_structure.json"),
    codebook_path: Path = typer.Option(CODEBOOK_FILE, help="Path to codebook.csv (updated in-place)"),
    save_intermediates: bool = typer.Option(False, "--save-intermediates", help="Write stage outputs for debugging"),
) -> None:
    """Build codebook with Spanish (item_text_es) and English (item_text_en) item texts."""
    logger.info("Stage 1 — extract Spanish items from structure JSON")
    items, structure = extract_spanish_items(json_path)

    logger.info("Stage 2 — build variable → item_text_es mapping")
    mapping = build_mapping(items, structure)

    logger.info("Stage 3 — update codebook CSV")
    update_codebook(codebook_path, mapping, save_intermediates=save_intermediates)


if __name__ == "__main__":
    app()
