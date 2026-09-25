"""Unit tests for the Figure 1 (floor effects) data preparation.

These run on a small handcrafted frame, not on the restricted dataset, so they
execute in CI. They pin the three decisions that define the published figure:
which variables are eligible, how they are ranked, and how ties are broken.
"""

import pandas as pd

from visia_q_dataset.plots import VALIDITY_SCORES, zero_score_rates


def _frame() -> pd.DataFrame:
    """Four participants per group with hand-chosen zero patterns.

    Zero rates per group (HR-G / PC-G / GC-G), in percent:
      a_score : 0 / 25 / 100
      b_score : 25 / 50 / 50    <- tie with c_score on GC-G, declared first
      c_score : 0 / 0 / 50      <- tie with b_score on GC-G, declared second
      ov_score: 100 / 100 / 100 <- validity indicator, must be dropped
    """
    return pd.DataFrame(
        {
            "clinical_group": [1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3],
            "a_score": [1, 2, 3, 4, 0, 1, 2, 3, 0, 0, 0, 0],
            "b_score": [0, 1, 2, 3, 0, 0, 1, 2, 0, 0, 1, 2],
            "c_score": [1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1],
            "ov_score": [0] * 12,
            "uuid": [f"fixture-{i:04d}" for i in range(12)],
        }
    )


def test_validity_indicators_are_excluded():
    rates = zero_score_rates(_frame())
    assert set(rates.index).isdisjoint(VALIDITY_SCORES)
    assert set(rates.index) == {"a_score", "b_score", "c_score"}


def test_ranked_by_control_group_zero_rate_descending():
    rates = zero_score_rates(_frame())
    control = rates["Normative (Control)"]
    assert list(control) == sorted(control, reverse=True)
    assert rates.index[0] == "a_score"


def test_ties_keep_original_column_order():
    # b_score and c_score both sit at 50% in GC-G; the published figure resolves
    # such ties by the column order of the dataset, which a stable sort preserves.
    rates = zero_score_rates(_frame())
    assert list(rates.index[1:]) == ["b_score", "c_score"]


def test_percentages_are_per_group_and_in_percent():
    rates = zero_score_rates(_frame())
    assert rates.loc["a_score", "Target (High-Risk)"] == 0.0
    assert rates.loc["a_score", "Confounder (Psychiatric)"] == 25.0
    assert rates.loc["a_score", "Normative (Control)"] == 100.0


def test_unscored_participants_leave_the_denominator():
    # A participant whose MACI-II protocol could not be scored has no value to
    # compare against zero; counting them as a non-zero score would understate
    # the floor effect of their group.
    frame = _frame()
    frame.loc[frame.index[10:], "a_score"] = pd.NA  # 2 of the 4 GC-G rows

    rates = zero_score_rates(frame)
    # GC-G keeps two valid a_score values, both zero, so the rate stays 100%
    # instead of dropping to 50% as it would if the blanks counted as non-zero.
    assert rates.loc["a_score", "Normative (Control)"] == 100.0
    # The other groups are untouched.
    assert rates.loc["a_score", "Confounder (Psychiatric)"] == 25.0


def test_a_group_with_no_valid_score_is_not_reported_as_zero():
    frame = _frame()
    frame.loc[frame.index[8:], "a_score"] = pd.NA  # every GC-G row

    rates = zero_score_rates(frame)
    assert pd.isna(rates.loc["a_score", "Normative (Control)"])
