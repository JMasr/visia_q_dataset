"""Unit tests for the two curation rules, on a small handcrafted frame."""

import pandas as pd

from visia_q_dataset.curate import ECIP_ITEMS, ECIP_SCORE, MACI_SCALES, curate, decode_ecip_items


def test_zero_stays_zero_and_other_values_lose_one():
    # The batch that wrote "No" as 0 keeps it; its endorsed levels start at 2.
    zero_based = pd.DataFrame([[0, 2, 3, 4]])
    assert decode_ecip_items(zero_based).values.tolist() == [[0, 1, 2, 3]]

    # The batch that wrote "No" as 1 shifts everything down by one.
    one_based = pd.DataFrame([[1, 2, 3, 5]])
    assert decode_ecip_items(one_based).values.tolist() == [[0, 1, 2, 4]]


def _frame() -> pd.DataFrame:
    rows = [
        {"uuid": "a", **{c: 0 for c in ECIP_ITEMS}, ECIP_SCORE: 0, **{c: 3 for c in MACI_SCALES}},
        {"uuid": "b", **{c: 1 for c in ECIP_ITEMS}, ECIP_SCORE: 0, **{c: 5 for c in MACI_SCALES}},
        {"uuid": "c", **{c: 2 for c in ECIP_ITEMS}, ECIP_SCORE: 99, **{c: -1 for c in MACI_SCALES}},
    ]
    frame = pd.DataFrame(rows)
    frame.loc[2, MACI_SCALES[0]] = 0  # a stray 0 inside an unscored profile
    return frame


def test_items_land_on_the_instrument_scale():
    curated, _ = curate(_frame())
    assert curated[ECIP_ITEMS].min().min() == 0
    assert curated[ECIP_ITEMS].max().max() == 1


def test_score_is_recomputed_from_the_items():
    curated, _ = curate(_frame())
    assert (curated[ECIP_SCORE] == curated[ECIP_ITEMS].sum(axis=1)).all()
    assert curated.loc[2, ECIP_SCORE] == 22  # was 99


def test_an_unscored_profile_is_blanked_in_full():
    curated, _ = curate(_frame())
    # Including the scale that held a 0: a protocol that could not be scored on
    # fourteen scales was not scored on the fifteenth either.
    assert curated.loc[2, MACI_SCALES].isna().all()
    assert curated.loc[[0, 1], MACI_SCALES].notna().all().all()


def test_every_changed_cell_is_recorded():
    frame = _frame()
    curated, changes = curate(frame)
    assert set(changes["rule"]) == {"ecip-decode", "ecip-score-recompute", "maci-unscored"}
    assert len(changes[changes["rule"] == "maci-unscored"]) == len(MACI_SCALES)
    for _, change in changes.iterrows():
        assert str(frame.at[change["row"], change["column"]]) == str(change["before"])
