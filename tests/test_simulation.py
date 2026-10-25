"""Hand-checkable cases for the staffing simulator (rules: docs/assumptions.md D3, D5, D6).

Day 0 is 2026-01-01. Feb 1 is day 31, Mar 1 is day 59, Mar 2 is day 60.
Budget is $10,000 for every advertiser, so annual-basis uplift is $1,350 each.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.schemas import RESULTS_COLUMNS, validate
from src.simulation.simulator import simulate_country, simulate_plan

BUDGET = 10_000
UPLIFT_EACH = BUDGET * 0.135
SALARY = 12_000  # $1,000 a month


def run(arrivals, agents=1, hires=None, terms=None):
    """arrivals: {day_index: count}; hires/terms: {month_number: count}."""
    daily = np.zeros(365)
    for day, n in arrivals.items():
        daily[day] = n
    hires, terms = hires or {}, terms or {}
    return simulate_country(
        daily_arrivals=daily,
        daily_budget=np.full(365, BUDGET),
        agents_start=agents,
        hires=[hires.get(m, 0) for m in range(1, 13)],
        terminations=[terms.get(m, 0) for m in range(1, 13)],
        annual_salary=SALARY,
    )


def test_capacity_is_ten_per_agent_and_the_rest_wait():
    r = run({0: 15})
    assert r.loc["2026-01", "advertisers_supported"] == 10
    assert r.loc["2026-01", "advertisers_waiting"] == 5


def test_slots_free_after_sixty_days_of_support():
    r = run({0: 10, 1: 10})
    # Second batch waits until the first graduates on day 60 (Mar 2).
    assert r.loc["2026-02", "advertisers_supported"] == 0
    assert r.loc["2026-03", "advertisers_supported"] == 10
    assert r.loc["2026-03", "average_wait_days"] == 59


def test_can_be_assigned_on_day_sixty_of_waiting():
    r = run({0: 20})
    assert r.loc["2026-03", "advertisers_supported"] == 10
    assert r.loc["2026-03", "average_wait_days"] == 60
    assert r["advertisers_expired"].sum() == 0


def test_unserved_advertisers_expire_after_sixty_days():
    r = run({0: 5}, agents=0)
    assert r.loc["2026-02", "advertisers_waiting"] == 5
    assert r.loc["2026-03", "advertisers_expired"] == 5
    assert r.loc["2026-03", "advertisers_waiting"] == 0


def test_hire_is_paid_while_training_and_productive_next_month():
    r = run({0: 5}, agents=0, hires={1: 1})
    assert r.loc["2026-01", "advertisers_supported"] == 0
    assert r.loc["2026-01", "agents_in_training"] == 1
    assert r.loc["2026-01", "salary_cost_usd"] == pytest.approx(1_000)
    assert r.loc["2026-02", "agents_active"] == 1
    assert r.loc["2026-02", "advertisers_supported"] == 5
    assert r.loc["2026-02", "average_wait_days"] == 31


def test_agent_on_notice_takes_no_new_advertisers():
    r = run({0: 15}, agents=2, terms={1: 1})
    assert r.loc["2026-01", "advertisers_supported"] == 10


def test_termination_costs_and_salary_through_notice_month():
    r = run({}, agents=2, terms={1: 1})
    assert r.loc["2026-01", "termination_cost_usd"] == pytest.approx(0.4 * SALARY)
    assert r.loc["2026-01", "salary_cost_usd"] == pytest.approx(2_000)
    assert r.loc["2026-02", "salary_cost_usd"] == pytest.approx(1_000)
    assert r.loc["2026-02", "agents_active"] == 1


def test_departing_agents_advertisers_lose_support_when_no_free_slots():
    # 20 assigned on Jan 1 graduate on day 60; one agent leaves Mar 1 (day 59).
    r = run({0: 20}, agents=2, terms={2: 1})
    assert r.loc["2026-03", "advertisers_support_lost"] == 10
    assert r.loc["2026-03", "incremental_revenue_usd"] == pytest.approx(-10 * UPLIFT_EACH)


def test_revenue_is_booked_when_support_starts():
    r = run({0: 4})
    assert r.loc["2026-01", "incremental_revenue_usd"] == pytest.approx(4 * UPLIFT_EACH)
    assert r.loc["2026-01", "net_value_usd"] == pytest.approx(4 * UPLIFT_EACH - 1_000)


def test_utilization_is_occupied_share_of_capacity():
    r = run({0: 10})
    assert r.loc["2026-01", "utilization"] == pytest.approx(1.0)


def test_fractional_advertisers_are_allowed():
    r = run({0: 10.5})
    assert r.loc["2026-01", "advertisers_supported"] == 10
    assert r.loc["2026-01", "advertisers_waiting"] == pytest.approx(0.5)


def test_terminating_more_agents_than_employed_raises():
    with pytest.raises(ValueError, match="terminat"):
        run({}, agents=1, terms={1: 2})


SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sample"


def test_simulate_plan_on_samples_matches_results_contract():
    out = simulate_plan(
        pd.read_csv(SAMPLE / "sample_demand.csv"),
        pd.read_csv(SAMPLE / "sample_staffing_plan.csv"),
        pd.read_csv(SAMPLE / "sample_country_parameters.csv"),
    )
    validate(out, RESULTS_COLUMNS, "simulate_plan output")
    assert len(out) == 22 * 12
    assert (out["advertisers_waiting"] >= 0).all()
