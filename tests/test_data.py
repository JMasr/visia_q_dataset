from pathlib import Path

import pandas as pd

from visia_q_dataset.config import RAW_DATA_FILE
from visia_q_dataset.dataset import (
    filter_all_valid,
    filter_maci_valid,
    filter_oviedo_negative,
)
from visia_q_dataset.validation import EXPECTED_COLUMNS, validate_raw_dataset


def test_validate_raw_dataset_ok():
    assert validate_raw_dataset(RAW_DATA_FILE)


def test_validate_raw_dataset_bad_shape(tmp_path: Path):
    bad_path = tmp_path / "bad.csv"
    pd.DataFrame(columns=EXPECTED_COLUMNS).to_csv(bad_path, index=False)
    assert not validate_raw_dataset(bad_path)


def test_filter_all_valid(tmp_path: Path):
    df = pd.read_csv(RAW_DATA_FILE)
    expected = df[(df["ov_score"] <= 2) & (df["maci_score_inval"] == 0)]
    output_path = tmp_path / "all_valid.csv"

    filter_all_valid(input_path=RAW_DATA_FILE, output_path=output_path, skip_safeguard=False)

    result = pd.read_csv(output_path)
    assert result.shape == expected.shape
    pd.testing.assert_frame_equal(
        result.reset_index(drop=True),
        expected.reset_index(drop=True),
        check_dtype=False,
    )


def test_filter_oviedo_negative(tmp_path: Path):
    df = pd.read_csv(RAW_DATA_FILE)
    expected = df[df["ov_score"] <= 2]
    output_path = tmp_path / "oviedo_neg.csv"

    filter_oviedo_negative(
        input_path=RAW_DATA_FILE, output_path=output_path, skip_safeguard=False
    )

    result = pd.read_csv(output_path)
    assert result.shape == expected.shape
    pd.testing.assert_frame_equal(
        result.reset_index(drop=True),
        expected.reset_index(drop=True),
        check_dtype=False,
    )


def test_filter_maci_valid(tmp_path: Path):
    df = pd.read_csv(RAW_DATA_FILE)
    expected = df[df["maci_score_inval"] == 0]
    output_path = tmp_path / "maci_valid.csv"

    filter_maci_valid(input_path=RAW_DATA_FILE, output_path=output_path, skip_safeguard=False)

    result = pd.read_csv(output_path)
    assert result.shape == expected.shape
    pd.testing.assert_frame_equal(
        result.reset_index(drop=True),
        expected.reset_index(drop=True),
        check_dtype=False,
    )
