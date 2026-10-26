"""Member 3 — Staffing optimization.

Owner: Mer McFadden
Branch: feature/optimization

Objective (D8): maximize total 2026 net value (uplift - salary - termination cost).
Countries don't share agents (D6), so each country is planned on its own.

A country's plan is described by the productive headcount it aims for after each
month's decision takes effect: level k is the headcount from the 1st of month k+1
(level 11 is Jan 1, 2027). Raising a level means hiring in month k; lowering it
means giving notice in month k. Every level >= 0 is a valid plan, and a plan never
hires and terminates in the same month.

Search (a documented heuristic, not a guaranteed optimum):
  1. Start from "keep the starting staff", a demand-based plan (enough agents to hold
     everyone who arrived in the previous 60 days), and a leaner version of it (80%).
  2. Local search: nudge one month's level, or every level from a month onward, up or
     down by a step; keep any change that raises net value. Steps shrink by half
     down to 1 agent. Each candidate is scored with simulate_country.
  3. Keep the best result over the three starts.
Because "keep the starting staff" is a start, the result is never worse than it.
"""

import math
from typing import Callable

import numpy as np
import pandas as pd

from src.schemas import COUNTRY_PARAMETERS_COLUMNS, DEMAND_COLUMNS, STAFFING_PLAN_COLUMNS, validate
from src.simulation.simulator import (
    AGENT_CAPACITY, EPS, MONTH_OF_DAY, MONTHS, SUPPORT_DAYS, daily_inputs, simulate_country,
    simulate_plan,
)


def year_end_need(daily_arrivals) -> int:
    """Agents needed on Jan 1, 2027 to hold everyone still in support, assuming each
    2026 arrival started support on arrival. Used by the optional year-end floor."""
    arrivals = np.asarray(daily_arrivals, dtype=float)
    in_support = arrivals[len(arrivals) - SUPPORT_DAYS + 1:].sum()
    return math.ceil(in_support / AGENT_CAPACITY - EPS)


def _demand_levels(arrivals) -> list[int]:
    """Headcount that holds everyone who arrived in the trailing 60 days, at the
    month's busiest day, for each month a level applies to."""
    trailing = np.convolve(arrivals, np.ones(SUPPORT_DAYS))[:len(arrivals)]
    need = [math.ceil(trailing[MONTH_OF_DAY == mo].max() / AGENT_CAPACITY - EPS)
            for mo in range(12)]
    return need[1:] + need[-1:]  # level k applies from month k+1; Jan 2027 uses December


def _plan_from_levels(start: int, levels) -> tuple[list[int], list[int]]:
    change = np.diff([start, *levels])
    return [int(max(c, 0)) for c in change], [int(max(-c, 0)) for c in change]


def optimize_country(
    daily_arrivals,
    daily_budget,
    agents_start: int,
    annual_salary: float,
    uplift_basis: str = "annual",
    year_end_floor: bool = False,
) -> tuple[list[int], list[int]]:
    """Best plan found for one country. Returns (hires, terminations), 12 ints each.

    year_end_floor=True requires at least year_end_need(daily_arrivals) agents on
    Jan 1, 2027, so the plan doesn't leave 2027 short-staffed (see D8).
    Invalid inputs raise ValueError (the simulator's checks).
    """
    arrivals = np.asarray(daily_arrivals, dtype=float)
    budget = np.asarray(daily_budget, dtype=float)
    scores = {}

    def score(levels):
        key = tuple(levels)
        if key not in scores:
            hires, terms = _plan_from_levels(start, levels)
            scores[key] = simulate_country(
                arrivals, budget, start, hires, terms, annual_salary, uplift_basis
            )["net_value_usd"].sum()
        return scores[key]

    # Validates every input before anything is derived from them.
    simulate_country(arrivals, budget, agents_start, [0] * 12, [0] * 12, annual_salary, uplift_basis)
    start = int(agents_start)
    floor = year_end_need(arrivals) if year_end_floor else 0

    def with_floor(levels):
        return [*levels[:11], max(levels[11], floor)]

    def improve(best):
        step = 1 << max(max(best), 1).bit_length()
        while step >= 1:
            improved = True
            while improved:
                improved = False
                for k in range(12):
                    for stop in (k + 1, 12):  # this month only, or from this month on
                        for sign in (1, -1):
                            cand = list(best)
                            cand[k:stop] = [v + sign * step for v in cand[k:stop]]
                            if min(cand) < 0 or cand[11] < floor:
                                continue
                            if score(cand) > score(best) + 1e-6:
                                best, improved = cand, True
            step //= 2
        return best

    need = _demand_levels(arrivals)
    starts = [[start] * 12, need, [math.ceil(0.8 * n) for n in need]]
    best = improve(max((with_floor(s) for s in starts), key=score))
    return _plan_from_levels(start, best)


def optimize_staffing(
    demand_df: pd.DataFrame,
    country_parameters_df: pd.DataFrame,
    simulate_fn: Callable[..., pd.DataFrame] = simulate_plan,
    uplift_basis: str = "annual",
    year_end_floor: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Search staffing plans for every country and pick the one with the best net value.

    `simulate_fn` has the signature of src.simulation.simulator.simulate_plan and is
    used once, to evaluate the recommended plan. The search itself scores candidates
    with simulate_country, which follows the same rules.

    Returns (recommended_plan_df, evaluated_results_df):
      recommended_plan_df  -> STAFFING_PLAN_COLUMNS
      evaluated_results_df -> RESULTS_COLUMNS (this becomes outputs/plan_2026.csv)
    """
    validate(demand_df, DEMAND_COLUMNS, "demand_df")
    validate(country_parameters_df, COUNTRY_PARAMETERS_COLUMNS, "country_parameters_df")
    # Run the do-nothing plan first so mismatched tables fail with the simulator's message.
    simulate_plan(demand_df, pd.DataFrame(columns=STAFFING_PLAN_COLUMNS), country_parameters_df,
                  uplift_basis)

    rows = []
    for p in country_parameters_df.itertuples(index=False):
        arrivals, budget = daily_inputs(demand_df, p.country)
        try:
            hires, terms = optimize_country(arrivals, budget, p.agents_jan_2026,
                                            p.annual_salary_usd, uplift_basis, year_end_floor)
        except ValueError as e:
            raise ValueError(f"{p.country}: {e}") from e
        rows += [(p.country, mo, h, x) for mo, h, x in zip(MONTHS, hires, terms)]
    plan = pd.DataFrame(rows, columns=STAFFING_PLAN_COLUMNS)

    if uplift_basis == "annual":
        results = simulate_fn(demand_df, plan, country_parameters_df)
    else:
        results = simulate_fn(demand_df, plan, country_parameters_df, uplift_basis=uplift_basis)
    return plan, results


if __name__ == "__main__":
    # python -m src.optimization.optimizer  ->  outputs/plan_2026.csv and staffing_plan_2026.csv
    from src.optimization.scenarios import write_outputs

    for path in write_outputs():
        print(f"wrote {path}")
