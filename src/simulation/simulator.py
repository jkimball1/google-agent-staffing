"""Member 2 — Staffing simulation.

Owner: Mer McFadden
Branch: feature/simulation

Simulates day by day, summarizes by month. Rules (see docs/assumptions.md D3, D5, D6):
  - all agents start 2026 with no advertisers assigned
  - each productive agent supports at most 10 advertisers at a time
  - each advertiser is supported for 60 days, then frees the slot
  - unassigned advertisers wait up to 60 days, then expire (no uplift)
  - hires take one month of training before becoming productive
  - terminations need one month of notice; cost 40% of annual salary

Each country's agents are modeled as one shared pool. Agents serving notice keep
their current advertisers but take no new ones, and new assignments are limited to
what the agents who are staying can hold: free slots = 10 x staying agents - all
occupied slots. So while someone is on notice, the pool keeps room to absorb their
advertisers when they leave.
"""

import numpy as np
import pandas as pd

from src.optimization.financials import incremental_revenue, termination_cost
from src.schemas import (
    COUNTRY_PARAMETERS_COLUMNS, DEMAND_COLUMNS, RESULTS_COLUMNS, STAFFING_PLAN_COLUMNS, validate,
)

AGENT_CAPACITY = 10
SUPPORT_DAYS = 60
MAX_WAIT_DAYS = 60
EPS = 1e-9  # ignore floating-point crumbs when comparing slot counts

DATES = pd.date_range("2026-01-01", "2026-12-31", freq="D")
MONTHS = [f"2026-{m:02d}" for m in range(1, 13)]
MONTH_OF_DAY = DATES.month.to_numpy() - 1           # 0..11 for each day
FIRST_OF_MONTH = DATES.day.to_numpy() == 1

# Extra column beyond RESULTS_COLUMNS: advertisers whose support was cut short
# because their agent left and nobody had a free slot (D5).
EXTRA_COLUMNS = ["advertisers_support_lost"]


def simulate_country(
    daily_arrivals,
    daily_budget,
    agents_start: int,
    hires,
    terminations,
    annual_salary: float,
    uplift_basis: str = "annual",
) -> pd.DataFrame:
    """Simulate one country for 2026.

    daily_arrivals, daily_budget: length-365 arrays (eligible sign-ups and their mean budget).
    hires, terminations: length-12 sequences, decided on the 1st of each month.
    Returns one row per month (index "2026-01".."2026-12") with the RESULTS_COLUMNS
    metrics (no country/month columns) plus EXTRA_COLUMNS.
    """
    arrivals = np.asarray(daily_arrivals, dtype=float)
    budget = np.asarray(daily_budget, dtype=float)
    n_days = len(DATES)

    waiting = np.zeros(n_days)        # by arrival day
    occupied = np.zeros(n_days)       # by support start day
    occupied_value = np.zeros(n_days)  # revenue booked for those advertisers
    occupied_total = 0.0

    productive, on_notice, training = int(agents_start), 0, 0
    m = {k: np.zeros(12) for k in [
        "forecast_eligible", "agents_active", "agents_in_training", "agents_hired",
        "agents_terminated", "advertisers_supported", "advertisers_waiting",
        "advertisers_expired", "wait_days_total", "utilization_sum", "days",
        "incremental_revenue_usd", "salary_cost_usd", "termination_cost_usd",
        "advertisers_support_lost"]}

    for t in range(n_days):
        mo = MONTH_OF_DAY[t]

        # 1. Graduations
        s = t - SUPPORT_DAYS
        if s >= 0 and occupied[s] > 0:
            occupied_total -= occupied[s]
            occupied[s] = occupied_value[s] = 0.0

        # 2. Staffing changes on the 1st: last month's notices leave, trainees start,
        #    then this month's hires and terminations take effect.
        if FIRST_OF_MONTH[t]:
            on_notice = 0
            productive += training
            training = int(hires[mo])
            leaving = int(terminations[mo])
            if leaving > productive:
                raise ValueError(
                    f"Cannot terminate {leaving} agents in {MONTHS[mo]}: "
                    f"only {productive} productive agents are employed")
            productive -= leaving
            on_notice = leaving

            holding = AGENT_CAPACITY * (productive + on_notice)
            if occupied_total > holding + EPS:
                keep = holding / occupied_total
                # Lost advertisers forfeit uplift for the support days they miss (D5).
                days_left = np.clip(np.arange(n_days) + SUPPORT_DAYS - t, 0, SUPPORT_DAYS)
                m["advertisers_support_lost"][mo] += occupied_total - holding
                m["incremental_revenue_usd"][mo] -= (
                    occupied_value * (1 - keep) * days_left / SUPPORT_DAYS).sum()
                occupied *= keep
                occupied_value *= keep
                occupied_total = float(holding)

            m["agents_active"][mo] = productive + on_notice
            m["agents_in_training"][mo] = training
            m["agents_hired"][mo] = training
            m["agents_terminated"][mo] = leaving
            m["salary_cost_usd"][mo] = (productive + on_notice + training) * annual_salary / 12
            m["termination_cost_usd"][mo] = termination_cost(leaving, annual_salary)

        # 3. Expiries: anyone who has waited more than MAX_WAIT_DAYS
        e = t - MAX_WAIT_DAYS - 1
        if e >= 0 and waiting[e] > 0:
            m["advertisers_expired"][mo] += waiting[e]
            waiting[e] = 0.0

        # 4. New arrivals join the back of the line
        waiting[t] += arrivals[t]
        m["forecast_eligible"][mo] += arrivals[t]

        # 5. Serve the line first-come, first-served
        free = AGENT_CAPACITY * productive - occupied_total
        if free > EPS:
            lo = max(0, t - MAX_WAIT_DAYS)
            line = waiting[lo:t + 1]
            ahead = np.cumsum(line) - line
            take = np.minimum(line, np.maximum(free - ahead, 0.0))
            n_taken = take.sum()
            if n_taken > 0:
                value = incremental_revenue(take, budget[lo:t + 1], uplift_basis).sum()
                waiting[lo:t + 1] -= take
                occupied[t] += n_taken
                occupied_value[t] += value
                occupied_total += n_taken
                m["advertisers_supported"][mo] += n_taken
                m["incremental_revenue_usd"][mo] += value
                m["wait_days_total"][mo] += (take * (t - np.arange(lo, t + 1))).sum()

        # 6. Daily bookkeeping
        capacity = AGENT_CAPACITY * (productive + on_notice)
        m["utilization_sum"][mo] += occupied_total / capacity if capacity else 0.0
        m["days"][mo] += 1
        m["advertisers_waiting"][mo] = waiting.sum()  # last day of month wins

    supported = m["advertisers_supported"]
    out = pd.DataFrame({
        "forecast_eligible": m["forecast_eligible"],
        "agents_active": m["agents_active"].astype(int),
        "agents_in_training": m["agents_in_training"].astype(int),
        "agents_hired": m["agents_hired"].astype(int),
        "agents_terminated": m["agents_terminated"].astype(int),
        "advertisers_supported": supported,
        "advertisers_waiting": m["advertisers_waiting"],
        "advertisers_expired": m["advertisers_expired"],
        "average_wait_days": np.divide(m["wait_days_total"], supported,
                                       out=np.zeros(12), where=supported > 0),
        "utilization": m["utilization_sum"] / m["days"],
        "incremental_revenue_usd": m["incremental_revenue_usd"],
        "salary_cost_usd": m["salary_cost_usd"],
        "termination_cost_usd": m["termination_cost_usd"],
        "advertisers_support_lost": m["advertisers_support_lost"],
    }, index=pd.Index(MONTHS, name="month"))
    out["total_cost_usd"] = out["salary_cost_usd"] + out["termination_cost_usd"]
    out["net_value_usd"] = out["incremental_revenue_usd"] - out["total_cost_usd"]
    return out


def simulate_plan(
    demand_df: pd.DataFrame,
    staffing_plan_df: pd.DataFrame,
    country_parameters_df: pd.DataFrame,
    uplift_basis: str = "annual",
) -> pd.DataFrame:
    """Run a staffing plan against demand.

    Inputs follow DEMAND_COLUMNS, STAFFING_PLAN_COLUMNS, COUNTRY_PARAMETERS_COLUMNS.
    Demand must already be eligibility-filtered (Role 1). Days missing from demand_df
    count as zero sign-ups; countries or months missing from the plan count as no
    hires or terminations. Inputs that don't line up raise one ValueError listing
    every problem. Returns one row per country-month with RESULTS_COLUMNS plus EXTRA_COLUMNS.
    """
    _check_inputs(demand_df, staffing_plan_df, country_parameters_df)
    demand = demand_df.assign(day=(pd.to_datetime(demand_df["date"]) - DATES[0]).dt.days)
    plan = staffing_plan_df.set_index(["country", "month"])

    frames = []
    for p in country_parameters_df.itertuples(index=False):
        d = demand[demand["country"] == p.country]
        arrivals = np.zeros(len(DATES))
        np.add.at(arrivals, d["day"].to_numpy(), d["eligible_signups"].to_numpy())
        country_mean = d["mean_annual_budget_usd"].mean()
        country_mean = 0.0 if pd.isna(country_mean) else country_mean
        budget = np.full(len(DATES), country_mean)
        # A missing budget only matters on days with sign-ups, and _check_inputs rejects those.
        budget[d["day"].to_numpy()] = d["mean_annual_budget_usd"].fillna(country_mean).to_numpy()

        def plan_column(col):
            return [int(plan[col].get((p.country, mo), 0)) for mo in MONTHS]

        result = simulate_country(
            arrivals, budget, p.agents_jan_2026,
            plan_column("hires_requested"), plan_column("terminations_requested"),
            p.annual_salary_usd, uplift_basis)
        frames.append(result.reset_index().assign(country=p.country))

    out = pd.concat(frames, ignore_index=True)
    return out[RESULTS_COLUMNS + EXTRA_COLUMNS]


def _check_inputs(demand_df, staffing_plan_df, country_parameters_df):
    """Raise one ValueError listing every way the three inputs fail to line up."""
    validate(demand_df, DEMAND_COLUMNS, "demand_df")
    validate(staffing_plan_df, STAFFING_PLAN_COLUMNS, "staffing_plan_df")
    validate(country_parameters_df, COUNTRY_PARAMETERS_COLUMNS, "country_parameters_df")
    problems = []
    params, demand, plan = country_parameters_df, demand_df, staffing_plan_df
    known = set(params["country"])

    if params["country"].duplicated().any():
        problems.append("country_parameters has duplicate countries: "
                        f"{sorted(params.loc[params['country'].duplicated(), 'country'])}")
    for col in ["annual_salary_usd", "agents_jan_2026"]:
        bad = params[col].isna() | (params[col] < 0)
        if bad.any():
            problems.append(f"country_parameters has missing or negative {col} for "
                            f"{sorted(params.loc[bad, 'country'])}")

    unknown = set(demand["country"]) - known
    if unknown:
        problems.append(f"demand has countries not in country_parameters: {sorted(unknown)}")
    missing = known - set(demand["country"])
    if missing:
        problems.append(f"countries with no demand rows: {sorted(missing)}")
    dates = pd.to_datetime(demand["date"], format="%Y-%m-%d", errors="coerce")
    if dates.isna().any():
        problems.append("demand has dates not in YYYY-MM-DD form, e.g. "
                        f"{demand.loc[dates.isna(), 'date'].iloc[0]!r}")
    elif (dates.dt.year != 2026).any():
        problems.append("demand has dates outside 2026, e.g. "
                        f"{demand.loc[dates.dt.year != 2026, 'date'].iloc[0]!r}")
    if demand.duplicated(["country", "date"]).any():
        problems.append("demand has duplicate (country, date) rows")
    signups = demand["eligible_signups"]
    if signups.isna().any() or (signups < 0).any():
        problems.append("demand has missing or negative eligible_signups")
    if (demand["mean_annual_budget_usd"].isna() & (signups > 0)).any():
        problems.append("demand has missing mean_annual_budget_usd on days with sign-ups")

    unknown = set(plan["country"]) - known
    if unknown:
        problems.append(f"plan has countries not in country_parameters: {sorted(unknown)}")
    bad_months = sorted(set(plan["month"].astype(str)) - set(MONTHS))
    if bad_months:
        problems.append(f"plan has month values other than 2026-01..2026-12: {bad_months[:5]}")
    if plan.duplicated(["country", "month"]).any():
        problems.append("plan has duplicate (country, month) rows")
    for col in ["hires_requested", "terminations_requested"]:
        x = pd.to_numeric(plan[col], errors="coerce")
        if (x.isna() | (x < 0) | (x % 1 != 0)).any():
            problems.append(f"plan {col} must be a whole number >= 0")

    if problems:
        raise ValueError("Simulator inputs don't line up:\n  - " + "\n  - ".join(problems))
