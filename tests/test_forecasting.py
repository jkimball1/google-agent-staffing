"""Tests for src/forecasting/forecast.py (Role 1)."""

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.forecasting import forecast as f
from src.schemas import COUNTRY_PARAMETERS_COLUMNS, DEMAND_COLUMNS

WORKBOOK = Path(__file__).resolve().parents[1] / "data" / "raw" / "DADS5250_Hackathon_Google_Data.xlsx"
needs_workbook = pytest.mark.skipif(not WORKBOOK.exists(), reason="course workbook not present")


def raw_signups(dates, budgets=None, country="Spain"):
    """Sign-ups as the workbook reads them: datetimes, plus '2025-02-29' as text."""
    return pd.DataFrame({
        "Advertiser_ID": [f"A{i:06d}" for i in range(len(dates))],
        "Country": country,
        "Sign_Up_Date": [d if d == "2025-02-29" else datetime.fromisoformat(d) for d in dates],
        "Projected_Annual_Budget": budgets if budgets is not None else [50_000] * len(dates),
    })


# --- clean_signups ---------------------------------------------------------------

def test_spread_assigns_feb29_records_to_feb_1_through_28_in_turn():
    s = f.clean_signups(raw_signups(["2025-02-29"] * 30 + ["2024-05-01"]))
    feb = s[s["Sign_Up_Date"].dt.month == 2]["Sign_Up_Date"]
    assert len(s) == 31 and len(feb) == 30
    assert feb.dt.day.value_counts().sort_index().tolist() == [2, 2] + [1] * 26
    assert pd.api.types.is_datetime64_any_dtype(s["Sign_Up_Date"])


@pytest.mark.parametrize("rule, expected", [
    ("drop", []), ("feb28", ["2025-02-28"] * 2), ("mar1", ["2025-03-01"] * 2)])
def test_other_feb29_rules(rule, expected):
    s = f.clean_signups(raw_signups(["2025-02-29", "2025-02-29", "2024-01-01"]), rule)
    moved = s[s["Sign_Up_Date"].dt.year == 2025]["Sign_Up_Date"].dt.strftime("%Y-%m-%d")
    assert moved.tolist() == expected
    assert len(s) == 1 + len(expected)


def test_clean_signups_rejects_unknown_rule_and_unexpected_text_dates():
    with pytest.raises(ValueError, match="feb29_rule"):
        f.clean_signups(raw_signups(["2024-01-01"]), "ignore")
    bad = raw_signups(["2025-02-29"])
    bad["Sign_Up_Date"] = ["2024-13-01"]
    with pytest.raises(ValueError, match="unexpected text dates"):
        f.clean_signups(bad)


def test_clean_signups_does_not_modify_its_input():
    raw = raw_signups(["2025-02-29", "2024-01-01"])
    f.clean_signups(raw)
    assert raw.loc[0, "Sign_Up_Date"] == "2025-02-29"


# --- eligibility, history, profile, trend ------------------------------------------

def test_eligibility_is_strictly_above_the_threshold():
    params = pd.DataFrame({"country": ["Spain"], "eligibility_threshold_usd": [10_000]})
    s = f.clean_signups(raw_signups(["2024-01-01"] * 3, budgets=[9_999, 10_000, 10_001]))
    assert f.eligible_signups(s, params)["Projected_Annual_Budget"].tolist() == [10_001]


def history_frame(rows):
    """{country: (24 monthly counts for 2024-01 .. 2025-12)} -> monthly_history layout."""
    months = [f"{y}-{m:02d}" for y in (2024, 2025) for m in range(1, 13)]
    return pd.DataFrame(rows, index=months).T.rename_axis(index="country", columns="month")


def test_seasonal_profile_averages_each_years_shares():
    flat = [10] * 12
    peak = [10] * 11 + [32]  # December holds 32/142 of that year
    profile = f.seasonal_profile(history_frame({"A": flat + peak}))
    assert profile.sum() == pytest.approx(1.0)
    assert profile[12] == pytest.approx((1 / 12 + 32 / 142) / 2)


def test_trend_uses_pooled_growth_when_countries_differ_only_by_noise():
    # Both countries shrink 10%: no spread between them, so each gets exactly -10%.
    hist = history_frame({"A": [100] * 12 + [90] * 12, "B": [50] * 12 + [45] * 12})
    annual = f.annual_forecast(hist).set_index("country")
    assert annual["growth_used"].tolist() == pytest.approx([-0.1, -0.1])
    assert annual.loc["A", "signups_2026"] == pytest.approx(1080 * 0.9)


def test_trend_keeps_real_country_differences_for_large_countries():
    hist = history_frame({"A": [10_000] * 12 + [12_000] * 12,
                          "B": [10_000] * 12 + [8_000] * 12})
    annual = f.annual_forecast(hist).set_index("country")
    assert (annual["growth_weight"] > 0.99).all()
    assert annual.loc["A", "growth_used"] == pytest.approx(0.2, abs=0.001)
    assert annual.loc["B", "growth_used"] == pytest.approx(-0.2, abs=0.001)


# --- on the real workbook ----------------------------------------------------------

@pytest.fixture(scope="module")
def demand():
    return f.forecast_demand(str(WORKBOOK))


@needs_workbook
def test_country_parameters_match_the_sample_file():
    params = f.load_country_parameters(str(WORKBOOK))
    sample = pd.read_csv(WORKBOOK.parents[1] / "sample" / "sample_country_parameters.csv")
    assert list(params.columns) == COUNTRY_PARAMETERS_COLUMNS
    pd.testing.assert_frame_equal(params, sample, check_dtype=False)


@needs_workbook
def test_demand_covers_every_country_and_day_of_2026(demand):
    assert list(demand.columns) == DEMAND_COLUMNS
    assert demand["country"].nunique() == 22
    assert len(demand) == 22 * 365
    assert demand.groupby("country")["date"].agg(["min", "max", "nunique"]).eq(
        pd.Series({"min": "2026-01-01", "max": "2026-12-31", "nunique": 365})).all().all()
    assert demand[["eligible_signups", "mean_annual_budget_usd"]].notna().all().all()
    assert (demand["eligible_signups"] > 0).all()


@needs_workbook
def test_demand_is_close_to_2025_with_a_q4_peak(demand):
    sheets = f._read_workbook(str(WORKBOOK))
    params = f.load_country_parameters(str(WORKBOOK))
    eligible = f.eligible_signups(f.clean_signups(sheets[f.SIGNUPS_SHEET]), params)
    n2025 = (eligible["Sign_Up_Date"].dt.year == 2025).sum()
    assert demand["eligible_signups"].sum() == pytest.approx(n2025, rel=0.05)

    monthly = demand.groupby(demand["date"].str[:7])["eligible_signups"].sum()
    q4 = monthly[["2026-10", "2026-11", "2026-12"]].mean()
    assert q4 > 1.2 * monthly.drop(["2026-10", "2026-11", "2026-12"]).mean()


@needs_workbook
def test_daily_values_are_constant_within_each_month(demand):
    by_month = demand.groupby(["country", demand["date"].str[:7]])
    assert np.allclose(by_month["eligible_signups"].std(), 0)
    assert (by_month["mean_annual_budget_usd"].nunique() == 1).all()
