"""Audit the non-recomputability of the released participant identifiers.

The `uuid` column of the VisIA-Q dataset holds RFC 4122 version-5 (name-based)
UUIDs derived from each participant's internal sequential study code under a
namespace that is private to the project and is not published.

A name-based UUID is deterministic: anyone who knows the namespace and the name
can recompute it. The security of the scheme therefore rests entirely on the
namespace being secret. This module tests that claim the way an attacker would:
it sweeps the namespaces an outsider could plausibly guess, crossed with the
study-code patterns used by the two recruitment sites, and checks whether any
candidate derivation reproduces a released identifier.

Run with:
    python -m visia_q_dataset.identifiers
    make uuid-audit

Exit code 0 means no candidate matched, i.e. the released identifiers could not
be reconstructed from public information.
"""

import itertools
from pathlib import Path
import uuid

from loguru import logger
import pandas as pd
import typer

from visia_q_dataset.config import RAW_DATA_FILE
from visia_q_dataset.validation import validate_raw_dataset

app = typer.Typer(add_completion=False)

# Strings an outsider could plausibly use to build a project-specific namespace:
# institution domains, project name, and dataset name.
NAMESPACE_SEEDS = [
    "uvigo.es",
    "visia",
    "VISIA",
    "visia.uvigo.es",
    "sergas.es",
    "chuvi",
    "visia_q",
    "visia-q",
]

# Site prefixes (both recruitment hospitals), generic subject prefixes, and none.
CODE_PREFIXES = [
    "CUNQ",
    "OU",
    "VIGO",
    "CHUO",
    "CHUVI",
    "HAC",
    "AC",
    "VISIA",
    "P",
    "SUJ",
    "ID",
    "S",
    "",
]
CODE_SEPARATORS = ["-", "_", "", ".", " "]
CODE_FORMATS = ["{p}{s}{n:04d}", "{p}{s}{n:03d}", "{p}{s}{n:02d}", "{p}{s}{n}"]
CODE_MAX_INDEX = 250


def candidate_namespaces() -> dict[str, uuid.UUID]:
    """The five standard RFC 4122 namespaces plus those derivable from public strings."""
    namespaces = {
        "DNS": uuid.NAMESPACE_DNS,
        "URL": uuid.NAMESPACE_URL,
        "OID": uuid.NAMESPACE_OID,
        "X500": uuid.NAMESPACE_X500,
        "NIL": uuid.UUID(int=0),
    }
    for seed in NAMESPACE_SEEDS:
        namespaces[f"DNS({seed})"] = uuid.uuid5(uuid.NAMESPACE_DNS, seed)
        namespaces[f"URL({seed})"] = uuid.uuid5(uuid.NAMESPACE_URL, seed)
    return namespaces


def candidate_names():
    """Study-code strings an outsider could enumerate, in both original and lower case."""
    for prefix, separator, fmt in itertools.product(CODE_PREFIXES, CODE_SEPARATORS, CODE_FORMATS):
        for index in range(CODE_MAX_INDEX):
            name = fmt.format(p=prefix, s=separator, n=index)
            yield name
            yield name.lower()


def audit_identifiers(released: set[str]) -> tuple[list[tuple[str, str]], int]:
    """Try to reconstruct `released` identifiers; return (matches, candidates tried)."""
    matches: list[tuple[str, str]] = []
    tried = 0
    for namespace_label, namespace in candidate_namespaces().items():
        for name in candidate_names():
            tried += 1
            if str(uuid.uuid5(namespace, name)) in released:
                matches.append((namespace_label, name))
    return matches, tried


@app.command()
def audit(
    input_path: Path = RAW_DATA_FILE,
    skip_safeguard: bool = typer.Option(False, help="Skip validation against the raw dataset."),
) -> None:
    """Verify that no released identifier can be recomputed from public information."""
    if not skip_safeguard and not validate_raw_dataset(input_path):
        logger.error("Dataset validation failed. Use --skip-safeguard to bypass.")
        raise typer.Exit(code=1)

    released = set(pd.read_csv(input_path)["uuid"].astype(str))
    matches, tried = audit_identifiers(released)

    print(f"\n{'=' * 68}")
    print("  PARTICIPANT IDENTIFIER AUDIT — namespace recomputability")
    print(f"{'=' * 68}\n")
    print(f"  Released identifiers : {len(released)}")
    print(f"  Namespaces swept     : {len(candidate_namespaces())}")
    print(f"  Candidates tried     : {tried:,}")
    print(f"  Matches              : {len(matches)}\n")

    if matches:
        print("  RECOMPUTED — the namespace is guessable. Released identifiers matched:")
        for namespace_label, name in matches[:20]:
            print(f"    - namespace {namespace_label}, name {name!r}")
        print(f"\n{'=' * 68}\n")
        raise typer.Exit(code=1)

    print("  No released identifier could be reconstructed from public information.")
    print(f"\n{'=' * 68}\n")
    raise typer.Exit(code=0)


if __name__ == "__main__":
    app()
