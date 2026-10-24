"""Generate the SYNTHETIC sample files in data/sample/.

These numbers are made up. They exist only so each module can be built and
tested against the agreed interfaces before the real pipeline exists.
Do not use them for any analysis or conclusions.

Run from the repo root:  python data/sample/make_samples.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).parent
rng = np.random.default_rng(5250)

# Placeholder countries. The real list of 22 comes from the course workbook.
COUNTRIES = {
    # country: (daily eligible sign-ups, mean budget, salary, threshold, starting agents)
    "Germany": (18.0, 42_000, 68_000, 25_000, 30),
    "Japan":   (14.0, 51_000, 61_000, 30_000, 22),
    "Brazil":  (22.0, 19_000, 24_000, 10_000, 35),
    "India":   (30.0, 12_000, 14_000,  6_000, 48),
}
MONTHS = [f"2026-{m:02d}" for m in range(1, 13)]


def make_country_parameters():
    rows = [
        {"country": c, "annual_salary_usd": sal, "eligibility_threshold_usd": thr,
         "agents_jan_2026": agents}
        for c, (_, _, sal, thr, agents) in COUNTRIES.items()
    ]
    return pd.DataFrame(rows)


def make_demand():
    dates = pd.date_range("2026-01-01", "2026-12-31", freq="D")
    rows = []
    for c, (daily, budget, *_) in COUNTRIES.items():
        season = 1 + 0.15 * np.sin(2 * np.pi * (dates.dayofyear - 60) / 365)
        signups = rng.poisson(daily * season)
        for d, s in zip(dates, signups):
            rows.append({"country": c, "date": d.strftime("%Y-%m-%d"),
                         "eligible_signups": float(s),
                         "mean_annual_budget_usd": round(budget * rng.uniform(0.9, 1.1), 2)})
    return pd.DataFrame(rows)


def make_staffing_plan():
    rows = []
    for c in COUNTRIES:
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
            revenue = supported * r.budget * 0.135 * 60 / 365
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
                "average_wait_days": round(float(rng.uniform(2, 25)), 1),
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
    params = make_country_parameters()
    demand = make_demand()
    plan = make_staffing_plan()
    results = make_results(demand, params, plan)

    params.to_csv(OUT / "sample_country_parameters.csv", index=False)
    demand.to_csv(OUT / "sample_demand.csv", index=False)
    plan.to_csv(OUT / "sample_staffing_plan.csv", index=False)
    results.to_csv(OUT / "sample_results.csv", index=False)
    print(f"Wrote {len(params)} params, {len(demand)} demand, {len(plan)} plan, "
          f"{len(results)} results rows to {OUT}")
