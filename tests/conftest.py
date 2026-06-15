import numpy as np
import pandas as pd
import pytest

from visia_q_dataset.validation import EXPECTED_COLUMNS


@pytest.fixture(scope="session")
def synthetic_dataset_path(tmp_path_factory):
    """10-row synthetic dataset with all 145 columns for CI filter-logic tests.

    Quality flag layout (controls which rows survive each filter):
      ov_score <= 2       : rows 0-3, 6-7  (6 rows pass)
      maci_score_inval==0 : rows 0-5       (6 rows pass)
      Both filters        : rows 0-3       (4 rows pass)
    """
    rng = np.random.default_rng(42)
    n = 10

    data = {col: rng.integers(0, 5, n).tolist() for col in EXPECTED_COLUMNS}

    data["uuid"] = [f"fixture-{i:04d}" for i in range(n)]
    data["clinical_group"] = [1, 1, 2, 2, 3, 3, 1, 2, 3, 1]
    data["female"] = [1, 0, 1, 1, 0, 1, 0, 1, 0, 1]
    data["age"] = [14, 15, 13, 16, 17, 12, 15, 14, 13, 16]
    data["education"] = [2, 2, 1, 3, 2, 1, 2, 2, 1, 3]
    data["ov_score"] = [0, 0, 0, 0, 3, 3, 0, 0, 4, 4]
    data["maci_score_inval"] = [0, 0, 0, 0, 0, 0, 1, 1, 1, 1]

    path = tmp_path_factory.mktemp("fixtures") / "visia_q_dataset_fixture.csv"
    pd.DataFrame(data)[EXPECTED_COLUMNS].to_csv(path, index=False)
    return path
