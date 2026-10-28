"""Member 1 — Data preparation and demand forecasting.

Owner: Jasper Kimball
Branch: feature/forecasting

Forecasts 2026 eligible advertiser arrivals per country (see docs/assumptions.md D1, D2):
  - eligible means Projected_Annual_Budget > the country's threshold (strictly)
  - the 920 sign-ups dated 2025-02-29 are spread evenly over Feb 1-28, 2025 (D1)
  - 2026 total = 2025 eligible sign-ups x that country's 2024->2025 growth, with the
    growth shrunk toward the all-country growth in proportion to its sampling noise
    (on this data the countries' differences are all within noise, so every country
    gets the all-country growth, about -1.5%)
  - monthly shape = one seasonal profile shared by all countries, averaged over
    2024 and 2025 (country-specific shapes didn't repeat from one year to the next)
  - each month's total is spread evenly over its days
  - mean annual budget = mean budget of the country's eligible sign-ups in 2024-2025
    (budgets show no trend or seasonality), held constant through 2026
"""

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from src.schemas import COUNTRY_PARAMETERS_COLUMNS, DEMAND_COLUMNS, validate

SIGNUPS_SHEET = "Advertiser Sign-ups"
FEB29_RULES = ("spread", "drop", "feb28", "mar1")
DATES_2026 = pd.date_range("2026-01-01", "2026-12-31", freq="D")
MONTHS_2026 = [f"2026-{m:02d}" for m in range(1, 13)]


@lru_cache(maxsize=2)
def _read_workbook(workbook_path: str) -> dict[str, pd.DataFrame]:
    # Reading the 500k-row sheet takes several seconds; both public loaders need it.
    if not Path(workbook_path).exists():
        raise FileNotFoundError(
            f"Course workbook not found at {workbook_path}. It isn't included in the repo; "
            "put your copy at data/raw/DADS5250_Hackathon_Google_Data.xlsx (see data/raw/README.md).")
    return pd.read_excel(workbook_path, sheet_name=None)


def load_workbook(workbook_path: str) -> dict[str, pd.DataFrame]:
    """Read every sheet of the course workbook into DataFrames, keyed by sheet name."""
    return {name: df.copy() for name, df in _read_workbook(str(workbook_path)).items()}


def clean_signups(signups: pd.DataFrame, feb29_rule: str = "spread") -> pd.DataFrame:
    """Clean raw 2024–2025 sign-ups.

    The 920 records dated 2025-02-29 are read as text, not dates. feb29_rule:
      "spread"  keep them, assigned in turn to Feb 1, 2, ..., 28 (D1, the default)
      "drop"    remove them
      "feb28"   move them all to Feb 28
      "mar1"    move them all to Mar 1
    Returns the same columns with Sign_Up_Date as datetime64.
    """
    if feb29_rule not in FEB29_RULES:
        raise ValueError(f"feb29_rule must be one of {FEB29_RULES}, got {feb29_rule!r}")
    s = signups.copy()
    bad = s["Sign_Up_Date"].map(lambda v: isinstance(v, str))
    unexpected = set(s.loc[bad, "Sign_Up_Date"]) - {"2025-02-29"}
    if unexpected:
        raise ValueError(f"unexpected text dates in sign-ups: {sorted(unexpected)[:5]}")

    if feb29_rule == "drop":
        s = s[~bad]
    elif feb29_rule == "spread":
        feb_days = pd.date_range("2025-02-01", "2025-02-28", freq="D")
        s.loc[bad, "Sign_Up_Date"] = [feb_days[i % len(feb_days)] for i in range(bad.sum())]
    else:
        s.loc[bad, "Sign_Up_Date"] = pd.Timestamp("2025-02-28" if feb29_rule == "feb28"
                                                  else "2025-03-01")
    s["Sign_Up_Date"] = pd.to_datetime(s["Sign_Up_Date"])
    return s.reset_index(drop=True)


def load_country_parameters(workbook_path: str) -> pd.DataFrame:
    """Return one row per country with COUNTRY_PARAMETERS_COLUMNS."""
    sheets = _read_workbook(str(workbook_path))
    params = sheets["Agent Salary and Threshold"].merge(
        sheets["Existing Agent Staffing"], on="Country", validate="one_to_one")
    params = params.rename(columns={
        "Country": "country",
        "Annual_Agent_Salary_USD": "annual_salary_usd",
        "Advertiser_Eligibility_Threshold_USD": "eligibility_threshold_usd",
        "Existing_Agent_Count": "agents_jan_2026",
    })
    return validate(params, COUNTRY_PARAMETERS_COLUMNS, "country_parameters_df")[
        COUNTRY_PARAMETERS_COLUMNS].reset_index(drop=True)


def eligible_signups(signups: pd.DataFrame, params: pd.DataFrame) -> pd.DataFrame:
    """Cleaned sign-ups whose budget is strictly above their country's threshold."""
    s = signups.merge(params[["country", "eligibility_threshold_usd"]],
                      left_on="Country", right_on="country", validate="many_to_one")
    return s[s["Projected_Annual_Budget"] > s["eligibility_threshold_usd"]].drop(
        columns="eligibility_threshold_usd")


def monthly_history(eligible: pd.DataFrame) -> pd.DataFrame:
    """Eligible sign-ups per country (rows) and month of 2024–2025 (columns, 'YYYY-MM')."""
    month = eligible["Sign_Up_Date"].dt.strftime("%Y-%m")
    history = eligible.groupby(["country", month]).size().unstack(fill_value=0)
    history.columns.name = "month"
    return history


def seasonal_profile(history: pd.DataFrame) -> pd.Series:
    """Share of a year's eligible sign-ups falling in each calendar month (sums to 1).

    Pooled across countries and averaged over the two years."""
    totals = history.sum(axis=0)
    by_year = pd.DataFrame({
        year: totals[[f"{year}-{m:02d}" for m in range(1, 13)]].to_numpy()
        for year in (2024, 2025)}, index=range(1, 13))
    shares = (by_year / by_year.sum(axis=0)).mean(axis=1)
    return shares / shares.sum()


def annual_forecast(history: pd.DataFrame) -> pd.DataFrame:
    """2026 eligible sign-ups per country from the 2024->2025 trend.

    Each country's log growth is shrunk toward the all-country log growth by its
    Poisson noise (1/n_2024 + 1/n_2025) relative to the real spread between countries,
    so small countries lean on the shared trend and big ones on their own."""
    n24 = history[[c for c in history.columns if c.startswith("2024")]].sum(axis=1)
    n25 = history[[c for c in history.columns if c.startswith("2025")]].sum(axis=1)
    log_growth = np.log(n25 / n24)
    noise = 1 / n24 + 1 / n25
    pooled = np.log(n25.sum() / n24.sum())
    between = max(log_growth.var(ddof=1) - noise.mean(), 0.0)
    weight = between / (between + noise)  # all zeros when between == 0
    growth = pooled + weight * (log_growth - pooled)
    return pd.DataFrame({
        "signups_2024": n24, "signups_2025": n25,
        "growth_observed": np.exp(log_growth) - 1,
        "growth_weight": weight,
        "growth_used": np.exp(growth) - 1,
        "signups_2026": n25 * np.exp(growth),
    }).reset_index()


def forecast_monthly(workbook_path: str, feb29_rule: str = "spread") -> pd.DataFrame:
    """2026 forecast by country and month: eligible_signups, mean_annual_budget_usd.

    The building block of forecast_demand, also handy for notebook tables and plots."""
    params = load_country_parameters(workbook_path)
    signups = clean_signups(_read_workbook(str(workbook_path))[SIGNUPS_SHEET], feb29_rule)
    eligible = eligible_signups(signups, params)
    history = monthly_history(eligible)
    profile = seasonal_profile(history)
    annual = annual_forecast(history).set_index("country")["signups_2026"]
    budget = eligible.groupby("country")["Projected_Annual_Budget"].mean()

    monthly = pd.DataFrame(
        np.outer(annual.to_numpy(), profile.to_numpy()),
        index=annual.index, columns=MONTHS_2026,
    ).rename_axis(index="country", columns="month").stack().rename("eligible_signups")
    monthly = monthly.reset_index()
    monthly["mean_annual_budget_usd"] = monthly["country"].map(budget).round(2)
    # Same country order as the workbook (and country_parameters_df).
    monthly["country"] = pd.Categorical(monthly["country"], categories=params["country"])
    monthly = monthly.sort_values(["country", "month"]).reset_index(drop=True)
    monthly["country"] = monthly["country"].astype(str)
    return monthly


def forecast_demand(workbook_path: str) -> pd.DataFrame:
    """Forecast daily eligible sign-ups for every country for all of 2026.

    Returns a DataFrame with DEMAND_COLUMNS (see INTERFACES.md): each month's
    forecast spread evenly over its days.
    """
    monthly = forecast_monthly(workbook_path)
    days = pd.DataFrame({"date": DATES_2026})
    days["month"] = days["date"].dt.strftime("%Y-%m")
    days["days_in_month"] = days["date"].dt.days_in_month
    daily = monthly.merge(days, on="month")
    daily["eligible_signups"] = daily["eligible_signups"] / daily["days_in_month"]
    daily["date"] = daily["date"].dt.strftime("%Y-%m-%d")
    return validate(daily, DEMAND_COLUMNS, "demand_df")[DEMAND_COLUMNS].reset_index(drop=True)
