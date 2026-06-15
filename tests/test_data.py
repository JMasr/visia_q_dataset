from pathlib import Path

import pandas as pd
import pytest

from visia_q_dataset.config import RAW_DATA_FILE
from visia_q_dataset.dataset import (
    filter_all_valid,
    filter_maci_valid,
    filter_oviedo_negative,
)
from visia_q_dataset.validation import EXPECTED_COLUMNS, validate_raw_dataset

# ---------------------------------------------------------------------------
# Integration tests — require the real raw dataset at data/raw/visia_q_dataset.csv
# Automatically skipped when the file is absent (CI environment).
# Run locally with: pytest -m integration
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.skipif(not RAW_DATA_FILE.exists(), reason="Real dataset not available")
def test_validate_raw_dataset_ok():
    assert validate_raw_dataset(RAW_DATA_FILE)


@pytest.mark.integration
@pytest.mark.skipif(not RAW_DATA_FILE.exists(), reason="Real dataset not available")
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


@pytest.mark.integration
@pytest.mark.skipif(not RAW_DATA_FILE.exists(), reason="Real dataset not available")
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


@pytest.mark.integration
@pytest.mark.skipif(not RAW_DATA_FILE.exists(), reason="Real dataset not available")
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


# ---------------------------------------------------------------------------
# Unit tests — use synthetic fixture from conftest.py, run in CI without real data
# ---------------------------------------------------------------------------


def test_validate_raw_dataset_bad_shape(tmp_path: Path):
    bad_path = tmp_path / "bad.csv"
    pd.DataFrame(columns=EXPECTED_COLUMNS).to_csv(bad_path, index=False)
    assert not validate_raw_dataset(bad_path)


def test_filter_all_valid_fixture(synthetic_dataset_path: Path, tmp_path: Path):
    """Rows 0-3 pass both ov_score<=2 and maci_score_inval==0 (4 rows)."""
    output_path = tmp_path / "all_valid.csv"
    filter_all_valid(
        input_path=synthetic_dataset_path, output_path=output_path, skip_safeguard=True
    )
    result = pd.read_csv(output_path)
    assert result.shape[0] == 4


def test_filter_oviedo_negative_fixture(synthetic_dataset_path: Path, tmp_path: Path):
    """Rows 0-3 and 6-7 have ov_score<=2 (6 rows total)."""
    output_path = tmp_path / "oviedo_neg.csv"
    filter_oviedo_negative(
        input_path=synthetic_dataset_path, output_path=output_path, skip_safeguard=True
    )
    result = pd.read_csv(output_path)
    assert result.shape[0] == 6


def test_filter_maci_valid_fixture(synthetic_dataset_path: Path, tmp_path: Path):
    """Rows 0-5 have maci_score_inval==0 (6 rows total)."""
    output_path = tmp_path / "maci_valid.csv"
    filter_maci_valid(
        input_path=synthetic_dataset_path, output_path=output_path, skip_safeguard=True
    )
    result = pd.read_csv(output_path)
    assert result.shape[0] == 6
