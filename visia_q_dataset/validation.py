from pathlib import Path

import pandas as pd
from loguru import logger

EXPECTED_ROW_COUNT = 207
EXPECTED_COLUMN_COUNT = 145
EXPECTED_COLUMNS = [
    "ebip_1",
    "ebip_2",
    "ebip_3",
    "ebip_4",
    "ebip_5",
    "ebip_6",
    "ebip_7",
    "ebip_8",
    "ebip_9",
    "ebip_10",
    "ebip_11",
    "ebip_12",
    "ebip_13",
    "ebip_14",
    "ebip_score",
    "ecip_1",
    "ecip_2",
    "ecip_3",
    "ecip_4",
    "ecip_5",
    "ecip_6",
    "ecip_7",
    "ecip_8",
    "ecip_9",
    "ecip_10",
    "ecip_11",
    "ecip_12",
    "ecip_13",
    "ecip_14",
    "ecip_15",
    "ecip_16",
    "ecip_17",
    "ecip_18",
    "ecip_19",
    "ecip_20",
    "ecip_21",
    "ecip_22",
    "ecip_score",
    "eupi_1",
    "eupi_2",
    "eupi_3",
    "eupi_4",
    "eupi_5",
    "eupi_6",
    "eupi_7",
    "eupi_8",
    "eupi_9",
    "eupi_10",
    "eupi_11",
    "eupi_score",
    "maci_score_intro",
    "maci_score_inhi",
    "maci_score_su",
    "maci_score_drama",
    "maci_score_ego",
    "maci_score_rebel",
    "maci_score_hostil",
    "maci_score_conform",
    "maci_score_resent",
    "maci_score_ag",
    "maci_score_borderline",
    "maci_score_suicide",
    "maci_score_inval",
    "maci_score_incons",
    "maci_score_suicide_thoughts",
    "maci_score_nssi",
    "mfq_1",
    "mfq_2",
    "mfq_3",
    "mfq_4",
    "mfq_5",
    "mfq_6",
    "mfq_7",
    "mfq_8",
    "mfq_9",
    "mfq_10",
    "mfq_11",
    "mfq_12",
    "mfq_13",
    "mfq_14",
    "mfq_15",
    "mfq_16",
    "mfq_17",
    "mfq_18",
    "mfq_19",
    "mfq_20",
    "mfq_21",
    "mfq_22",
    "mfq_23",
    "mfq_24",
    "mfq_25",
    "mfq_26",
    "mfq_27",
    "mfq_28",
    "mfq_29",
    "mfq_30",
    "mfq_31",
    "mfq_32",
    "mfq_33",
    "mfq_score",
    "ov_score",
    "paykel_1",
    "paykel_2",
    "paykel_3",
    "paykel_4",
    "paykel_5",
    "paykel_score",
    "sdq_1",
    "sdq_2",
    "sdq_3",
    "sdq_4",
    "sdq_5",
    "sdq_6",
    "sdq_7",
    "sdq_8",
    "sdq_9",
    "sdq_10",
    "sdq_11",
    "sdq_12",
    "sdq_13",
    "sdq_14",
    "sdq_15",
    "sdq_16",
    "sdq_17",
    "sdq_18",
    "sdq_19",
    "sdq_20",
    "sdq_21",
    "sdq_22",
    "sdq_23",
    "sdq_24",
    "sdq_25",
    "sdq_score_epc",
    "sdq_score_eh",
    "sdq_score_ese",
    "sdq_score_epr",
    "sdq_score_epp",
    "sdq_score_pi",
    "sdq_score_pe",
    "sdq_score",
    "education",
    "clinical_group",
    "female",
    "age",
    "uuid",
]


def validate_raw_dataset(input_path: Path) -> bool:
    if not input_path.exists():
        logger.error(
            f"Dataset not found at: {input_path}\n"
            "  → Request access and download it from Zenodo:\n"
            "     https://doi.org/10.5281/zenodo.20703908\n"
            f"  → Then place the file at: {input_path}"
        )
        return False

    df = pd.read_csv(input_path)
    ok = True

    if df.shape != (EXPECTED_ROW_COUNT, EXPECTED_COLUMN_COUNT):
        logger.warning(
            "Dataset shape mismatch. Expected "
            f"{EXPECTED_ROW_COUNT}x{EXPECTED_COLUMN_COUNT}, got {df.shape}."
        )
        ok = False

    if list(df.columns) != EXPECTED_COLUMNS:
        missing = [col for col in EXPECTED_COLUMNS if col not in df.columns]
        extra = [col for col in df.columns if col not in EXPECTED_COLUMNS]
        logger.warning("Dataset columns do not match the expected schema.")
        if missing:
            logger.warning(f"Missing columns: {missing}")
        if extra:
            logger.warning(f"Unexpected columns: {extra}")
        ok = False

    return ok
