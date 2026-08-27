"""Tests for the participant identifier audit.

These run without the raw dataset: the search space is fixed, and both controls
are constructed in the test itself.
"""

import uuid

from visia_q_dataset.identifiers import (
    CODE_MAX_INDEX,
    audit_identifiers,
    candidate_names,
    candidate_namespaces,
)

EXPECTED_NAMESPACES = 21
EXPECTED_CANDIDATES = 2_730_000


def test_namespace_sweep_covers_standard_and_derived():
    namespaces = candidate_namespaces()
    assert len(namespaces) == EXPECTED_NAMESPACES
    for standard in ("DNS", "URL", "OID", "X500", "NIL"):
        assert standard in namespaces


def test_search_space_matches_the_figure_reported_in_the_paper():
    names = sum(1 for _ in candidate_names())
    assert names * len(candidate_namespaces()) == EXPECTED_CANDIDATES


def test_audit_separates_recomputable_from_private_identifiers():
    """Both controls in a single sweep.

    The positive control matters most: an audit that always reports zero matches
    would prove nothing about the released identifiers. The negative control
    confirms that a UUID minted under a namespace outside the sweep survives it.
    """
    recomputable = str(uuid.uuid5(uuid.NAMESPACE_DNS, "CUNQ-001"))
    private_namespace = uuid.uuid5(uuid.NAMESPACE_DNS, "a-namespace-no-outsider-would-try")
    unreachable = str(uuid.uuid5(private_namespace, f"CUNQ-{CODE_MAX_INDEX + 1:03d}"))

    matches, tried = audit_identifiers({recomputable, unreachable})

    assert ("DNS", "CUNQ-001") in matches, "audit missed a deliberately recomputable identifier"
    assert len(matches) == 1, "audit reconstructed an identifier it should not have"
    assert tried == EXPECTED_CANDIDATES
