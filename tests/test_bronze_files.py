"""
Tests de qualité sur les fichiers Bronze (sans BigQuery).

    pytest -q

Par défaut, utilise le dossier daté le plus récent de data/bronze/.
Pour en cibler un autre : BRONZE_DIR=data/bronze/2026-10-22 pytest -q
"""
import json
import os
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


def _bronze_dir() -> Path:
    env = os.environ.get("BRONZE_DIR")
    if env:
        return Path(env)
    return sorted(p for p in (ROOT / "data" / "bronze").iterdir() if p.is_dir())[-1]


@pytest.fixture(scope="module")
def d():
    b = _bronze_dir()
    return {
        "analytics": pd.read_csv(b / "analytics.csv", dtype={"period": str}),
        "defs": pd.read_csv(b / "indicator_definitions.csv"),
        "ou": pd.read_csv(b / "org_units.csv"),
        "info": json.loads((b / "system_info.json").read_text(encoding="utf-8")),
    }


def test_server_info_present(d):
    assert d["info"]["version"]
    assert d["info"]["serverDate"]


def test_grain_is_unique(d):
    a = d["analytics"]
    assert not a.duplicated(["indicator_id", "org_unit_id", "period"]).any()


def test_periods_are_12_valid_months(d):
    periods = sorted(d["analytics"]["period"].unique())
    assert len(periods) == 12
    for p in periods:
        assert len(p) == 6 and 1 <= int(p[4:]) <= 12


def test_all_org_units_are_districts(d):
    ou = d["ou"].set_index("org_unit_id")
    ids = d["analytics"]["org_unit_id"].unique()
    assert set(ids) <= set(ou.index)
    assert (ou.loc[ids, "level"] == 2).all()
    assert len(ids) == 13


def test_all_indicators_have_definitions(d):
    assert set(d["analytics"]["indicator_id"]) <= set(d["defs"]["indicator_id"])


def test_org_unit_hierarchy_is_consistent(d):
    ou = d["ou"]
    assert ou["level"].min() == 1 and ou["level"].max() == 4
    roots = ou[ou["parent_id"].isna()]
    assert len(roots) == 1
    non_root = ou[ou["parent_id"].notna()]
    assert set(non_root["parent_id"]) <= set(ou["org_unit_id"])


def test_values_are_numeric_and_not_null(d):
    assert d["analytics"]["value"].notna().all()


def test_coverage_values_are_not_extreme(d):
    names = d["defs"].set_index("indicator_id")["name"]
    a = d["analytics"].assign(name=lambda x: x["indicator_id"].map(names))
    cov = a[a["name"].str.contains("Coverage")]
    assert (cov["value"] >= 0).all()
    assert (cov["value"] <= 200).all()


def test_known_issue_fic_adjusted_is_always_zero(d):
    """Problème connu du serveur de démo, voir docs/data_quality_findings.md.
    Si ce test échoue, le serveur a corrigé l'indicateur : retirer l'exclusion en Silver."""
    fic = d["analytics"][d["analytics"]["indicator_id"] == "IT8EAeFRAat"]
    assert len(fic) > 0 and (fic["value"] == 0).all()
