"""Generate the sample files in data/sample/ from the course workbook.

These are development stand-ins so each module can be built against the agreed
interfaces before the real pipeline exists. They are NOT the forecast or the plan.

  sample_country_parameters.csv  REAL values from the workbook (22 countries)
  sample_demand.csv              2025 eligible sign-ups replayed as 2026 (naive, not a forecast)
  sample_staffing_plan.csv       SYNTHETIC random hires/terminations
  sample_results.csv             SYNTHETIC rough approximation, not a simulation

Run from the repo root (needs data/raw/DADS5250_Hackathon_Google_Data.xlsx):
    python data/sample/make_samples.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
WORKBOOK = ROOT / "data" / "raw" / "DADS5250_Hackathon_Google_Data.xlsx"
OUT = Path(__file__).parent
rng = np.random.default_rng(5250)
MONTHS = [f"2026-{m:02d}" for m in range(1, 13)]


def make_country_parameters(sheets):
    sal = sheets["Agent Salary and Threshold"]
    staff = sheets["Existing Agent Staffing"]
    return sal.merge(staff, on="Country").rename(columns={
        "Country": "country",
        "Annual_Agent_Salary_USD": "annual_salary_usd",
        "Advertiser_Eligibility_Threshold_USD": "eligibility_threshold_usd",
        "Existing_Agent_Count": "agents_jan_2026",
    })


def make_demand(sheets, params):
    s = sheets["Advertiser Sign-ups"].copy()
    # 2025-02-29 is read as text. Provisional D1: spread those rows evenly over Feb 2025.
    bad = s["Sign_Up_Date"].map(lambda v: isinstance(v, str))
    feb_days = pd.date_range("2025-02-01", "2025-02-28", freq="D")
    s.loc[bad, "Sign_Up_Date"] = [feb_days[i % len(feb_days)] for i in range(bad.sum())]
    s["date"] = pd.to_datetime(s["Sign_Up_Date"])

    s = s.merge(params, left_on="Country", right_on="country")
    s = s[(s["date"].dt.year == 2025)
          & (s["Projected_Annual_Budget"] > s["eligibility_threshold_usd"])]
    s["date"] = s["date"] + pd.DateOffset(years=1)

    daily = (s.groupby(["country", "date"])
             .agg(eligible_signups=("Advertiser_ID", "size"),
                  mean_annual_budget_usd=("Projected_Annual_Budget", "mean"))
             .reset_index())

    # Fill days with no sign-ups so every country has all 365 days.
    full = pd.MultiIndex.from_product(
        [params["country"], pd.date_range("2026-01-01", "2026-12-31", freq="D")],
        names=["country", "date"])
    daily = daily.set_index(["country", "date"]).reindex(full).reset_index()
    daily["eligible_signups"] = daily["eligible_signups"].fillna(0).astype(float)
    country_mean = daily.groupby("country")["mean_annual_budget_usd"].transform("mean")
    daily["mean_annual_budget_usd"] = daily["mean_annual_budget_usd"].fillna(country_mean).round(2)
    daily["date"] = daily["date"].dt.strftime("%Y-%m-%d")
    return daily


def make_staffing_plan(params):
    rows = []
    for c in params["country"]:
        for m in MONTHS:
            rows.append({"country": c, "month": m,
                         "hires_requested": int(rng.integers(0, 4)),
                         "terminations_requested": int(rng.integers(0, 2))})
    return pd.DataFrame(rows)


def make_results(demand, params, plan):
    demand = demand.assign(month=demand["date"].str[:7])
    monthly = (demand.groupby(["country", "month"])
               .agg(forecast_eligible=("eligible_signups", "sum"),
                    budget=("mean_annual_budget_usd", "mean"))
               .reset_index())
    df = monthly.merge(plan, on=["country", "month"]).merge(params, on="country")

    rows = []
    for c, g in df.groupby("country", sort=False):
        active = int(g["agents_jan_2026"].iloc[0])
        prev_hires = prev_terms = 0
        for _, r in g.sort_values("month").iterrows():
            active = active + prev_hires - prev_terms
            capacity_new = active * 10 * 30 / 60  # rough slots freed per month
            supported = min(r.forecast_eligible, capacity_new)
            waiting = max(r.forecast_eligible - supported, 0) * 0.6
            expired = max(r.forecast_eligible - supported, 0) * 0.4
            revenue = supported * r.budget * 0.135
            salary = (active + r.hires_requested) * r.annual_salary_usd / 12
            term_cost = r.terminations_requested * 0.4 * r.annual_salary_usd
            rows.append({
                "country": c, "month": r.month,
                "forecast_eligible": round(r.forecast_eligible, 1),
                "agents_active": active,
                "agents_in_training": int(r.hires_requested),
                "agents_hired": int(r.hires_requested),
                "agents_terminated": int(r.terminations_requested),
                "advertisers_supported": round(supported, 1),
                "advertisers_waiting": round(waiting, 1),
                "advertisers_expired": round(expired, 1),
                "average_wait_days": round(float(rng.uniform(0, 5)), 1),
                "utilization": round(min(supported / max(capacity_new, 1), 1.0), 3),
                "incremental_revenue_usd": round(revenue, 2),
                "salary_cost_usd": round(salary, 2),
                "termination_cost_usd": round(term_cost, 2),
                "total_cost_usd": round(salary + term_cost, 2),
                "net_value_usd": round(revenue - salary - term_cost, 2),
            })
            prev_hires, prev_terms = int(r.hires_requested), int(r.terminations_requested)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    sheets = pd.read_excel(WORKBOOK, sheet_name=None)
    params = make_country_parameters(sheets)
    demand = make_demand(sheets, params)
    plan = make_staffing_plan(params)
    results = make_results(demand, params, plan)

    params.to_csv(OUT / "sample_country_parameters.csv", index=False)
    demand.to_csv(OUT / "sample_demand.csv", index=False)
    plan.to_csv(OUT / "sample_staffing_plan.csv", index=False)
    results.to_csv(OUT / "sample_results.csv", index=False)
    print(f"Wrote {len(params)} params, {len(demand)} demand, {len(plan)} plan, "
          f"{len(results)} results rows to {OUT}")
