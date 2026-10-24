"""Check that the sample files match the contracts in src/schemas.py.

Module owners: add your own tests in tests/test_<module>.py, and validate
your real outputs against the same schemas.
"""

from pathlib import Path

import pandas as pd
import pytest

from src.schemas import (
    COUNTRY_PARAMETERS_COLUMNS,
    DEMAND_COLUMNS,
    RESULTS_COLUMNS,
    STAFFING_PLAN_COLUMNS,
    validate,
)

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sample"


@pytest.mark.parametrize("filename, columns", [
    ("sample_demand.csv", DEMAND_COLUMNS),
    ("sample_country_parameters.csv", COUNTRY_PARAMETERS_COLUMNS),
    ("sample_staffing_plan.csv", STAFFING_PLAN_COLUMNS),
    ("sample_results.csv", RESULTS_COLUMNS),
])
def test_sample_matches_contract(filename, columns):
    validate(pd.read_csv(SAMPLE / filename), columns, filename)


def test_results_cover_every_country_month():
    results = pd.read_csv(SAMPLE / "sample_results.csv")
    countries = results["country"].nunique()
    assert len(results) == countries * 12
    assert sorted(results["month"].unique()) == [f"2026-{m:02d}" for m in range(1, 13)]


def test_validate_reports_missing_columns():
    with pytest.raises(ValueError, match="eligible_signups"):
        validate(pd.DataFrame({"country": [], "date": []}), DEMAND_COLUMNS)
