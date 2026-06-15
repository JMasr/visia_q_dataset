"""Unit tests for visia_q_dataset.codebook — no real data required."""
from pathlib import Path

import pandas as pd
import pytest

from visia_q_dataset.codebook import (
    _is_skip,
    _strip_embedded_oviedo,
    MACI_NAME_TO_COLUMN,
    SDQ_SCORE_NAME_TO_COLUMN,
    build_mapping,
    update_codebook,
)


# ---------------------------------------------------------------------------
# Stage 1 — skip / strip helpers
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "O6. Si estás leyendo esto, contesta sí.",
    "O7. La distancia entre Madrid y Barcelona es mayor que entre Madrid y Nueva York.",
    "1O En alguna ocasión he estado solo en casa",
    "2O Cuando estoy cansado o enfermo, a veces me apetece acostarme pronto en la cama.",
    "4O. Se llega antes de Madrid a Moscú en coche que en avión",
    "5O. En alguna ocasión he viajado en autobús",
    "xO. Aux",
    "Observaciones EBIP-Q",
    "Observaciones",
])
def test_is_skip_true(text):
    assert _is_skip(text)


@pytest.mark.parametrize("text", [
    "1. ¿Has sentido que la vida no merece la pena?",
    "6A Rebelde",
    "11. Digo o hago cosas por Internet que no sería capaz de decir/hacer en persona",
    "19 Otra gente de mi edad se mete conmigo o se burla de mí.",
])
def test_is_skip_false(text):
    assert not _is_skip(text)


def test_strip_embedded_oviedo_eupi_item_4():
    raw = (
        "4. Cada vez me gusta más pasar horas conectado/a a Internet,"
        "9O En alguna ocasión he visto una película en la televisión"
    )
    result = _strip_embedded_oviedo(raw)
    assert result == "4. Cada vez me gusta más pasar horas conectado/a a Internet"
    assert "9O" not in result


def test_strip_embedded_oviedo_eupi_item_10():
    raw = (
        "10. Cuando no puedo conectarme no paro de pensar si me estaré perdiendo algo importante,"
        "AO En alguna ocasión he visto a niños jugando en el parque"
    )
    result = _strip_embedded_oviedo(raw)
    assert result == "10. Cuando no puedo conectarme no paro de pensar si me estaré perdiendo algo importante"
    assert "AO" not in result


def test_strip_embedded_oviedo_noop_for_clean_items():
    clean = "1. Alguien me ha golpeado, me ha pateado o me ha empujado"
    assert _strip_embedded_oviedo(clean) == clean


# ---------------------------------------------------------------------------
# Stage 2 — build_mapping
# ---------------------------------------------------------------------------

def _minimal_structure(items_by_instrument: dict) -> dict:
    visia_q = {
        k: {"columns_with_items": v, "columns_with_scores": []}
        for k, v in items_by_instrument.items()
    }
    return {"VISIA_Q": visia_q}


def test_build_mapping_positional_ebip():
    items_by_instrument = {
        "EBIP": [
            "1. Alguien me ha golpeado, me ha pateado o me ha empujado",
            "2. Alguien me ha insultado",
        ]
    }
    structure = _minimal_structure(items_by_instrument)
    mapping = build_mapping(items_by_instrument, structure)
    assert mapping["ebip_1"] == "1. Alguien me ha golpeado, me ha pateado o me ha empujado"
    assert mapping["ebip_2"] == "2. Alguien me ha insultado"


def test_build_mapping_flags_ebip_14_manual_review():
    items_by_instrument = {"EBIP": [f"{i}. Item {i}" for i in range(1, 14)]}  # 13 items
    structure = _minimal_structure(items_by_instrument)
    mapping = build_mapping(items_by_instrument, structure)
    assert mapping.get("ebip_14") == "MANUAL_REVIEW"


def test_build_mapping_maci_name_based():
    items_by_instrument = {
        "MACI-II": ["1 Introvertido", "6A Rebelde", "1 Invalidez"]
    }
    structure = _minimal_structure(items_by_instrument)
    structure["VISIA_Q"]["MACI-II"]["columns_with_scores"] = ["OV", "FF Tendencia suicida"]
    mapping = build_mapping(items_by_instrument, structure)
    assert mapping["maci_score_intro"] == "1 Introvertido"
    assert mapping["maci_score_rebel"] == "6A Rebelde"
    assert mapping["maci_score_inval"] == "1 Invalidez"
    assert mapping["maci_score_suicide"] == "FF Tendencia suicida"


def test_build_mapping_sdq_subscale_scores():
    items_by_instrument = {"SDQ": [f"{i} item" for i in range(1, 26)]}  # 25 items
    structure = _minimal_structure(items_by_instrument)
    structure["VISIA_Q"]["SDQ"]["columns_with_scores"] = [
        "ov",
        "Escala de problemas de conducta",
        "PUNTUACIÓN TOTAL SDQ",
    ]
    mapping = build_mapping(items_by_instrument, structure)
    assert mapping["sdq_score_epc"] == "Escala de problemas de conducta"
    assert mapping["sdq_score"] == "PUNTUACIÓN TOTAL SDQ"
    assert "ov" not in mapping


# ---------------------------------------------------------------------------
# Stage 3 — update_codebook
# ---------------------------------------------------------------------------

_MINIMAL_ROWS = [
    {
        "variable": "ebip_1", "instrument": "EBIP-Q", "domain": "Bullying",
        "item_number": "1", "data_type": "Integer",
        "item_text": "", "description": "EBIP-Q item 1", "range_or_values": "0–4", "notes": "raw",
    },
    {
        "variable": "ebip_score", "instrument": "EBIP-Q", "domain": "Bullying",
        "item_number": "total", "data_type": "Integer",
        "item_text": "", "description": "EBIP-Q total score", "range_or_values": "0–56", "notes": "score",
    },
    {
        "variable": "uuid", "instrument": "Demographics", "domain": "Identifier",
        "item_number": "—", "data_type": "String",
        "item_text": "", "description": "Participant UUID", "range_or_values": "UUID", "notes": "",
    },
]


def test_update_codebook_adds_columns_and_renames(tmp_path: Path):
    codebook_path = tmp_path / "codebook.csv"
    pd.DataFrame(_MINIMAL_ROWS).to_csv(codebook_path, index=False)

    mapping = {"ebip_1": "1. Alguien me ha golpeado, me ha pateado o me ha empujado"}
    update_codebook(codebook_path, mapping)

    result = pd.read_csv(codebook_path, keep_default_na=False)
    assert "item_text_es" in result.columns
    assert "item_text_en" in result.columns
    assert "item_text" not in result.columns  # renamed → item_text_en

    row = result[result["variable"] == "ebip_1"].iloc[0]
    assert row["item_text_es"] == "1. Alguien me ha golpeado, me ha pateado o me ha empujado"
    assert row["item_text_en"] == ""  # was empty before renaming

    row_score = result[result["variable"] == "ebip_score"].iloc[0]
    assert row_score["item_text_es"] == ""  # score column — not in mapping


def test_update_codebook_column_order(tmp_path: Path):
    codebook_path = tmp_path / "codebook.csv"
    pd.DataFrame(_MINIMAL_ROWS).to_csv(codebook_path, index=False)
    update_codebook(codebook_path, {})

    result = pd.read_csv(codebook_path, keep_default_na=False)
    cols = list(result.columns)
    assert cols.index("item_text_es") == cols.index("item_number") + 1
    assert cols.index("item_text_en") == cols.index("item_text_es") + 1
    assert cols.index("item_text_en") < cols.index("data_type")
