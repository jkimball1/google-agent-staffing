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


def run(arrivals, agents=1, hires=None, terms=None, budgets=None, uplift_basis="annual"):
    """arrivals: {day_index: count}; budgets: {day_index: budget}; hires/terms: {month_number: count}."""
    daily = np.zeros(365)
    for day, n in arrivals.items():
        daily[day] = n
    budget = np.full(365, float(BUDGET))
    for day, b in (budgets or {}).items():
        budget[day] = b
    hires, terms = hires or {}, terms or {}
    return simulate_country(
        daily_arrivals=daily,
        daily_budget=budget,
        agents_start=agents,
        hires=[hires.get(m, 0) for m in range(1, 13)],
        terminations=[terms.get(m, 0) for m in range(1, 13)],
        annual_salary=SALARY,
        uplift_basis=uplift_basis,
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


@pytest.mark.parametrize("arrival_day, expiry_month", [
    (28, "2026-03"),  # Jan 29 + 61 days = Mar 31 (day 89)
    (29, "2026-04"),  # Jan 30 + 61 days = Apr 1 (day 90)
])
def test_expiry_happens_exactly_61_days_after_arrival(arrival_day, expiry_month):
    r = run({arrival_day: 5}, agents=0)
    assert r.loc[expiry_month, "advertisers_expired"] == 5


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
    # They miss 1 of their 60 days, so 1/60 of their uplift is removed (D5).
    assert r.loc["2026-03", "incremental_revenue_usd"] == pytest.approx(-10 * UPLIFT_EACH / 60)


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


def test_remaining_agent_takes_over_what_fits_and_the_rest_lose_support():
    r = run({0: 15}, agents=2, terms={2: 1})
    assert r.loc["2026-03", "advertisers_support_lost"] == 5
    assert r.loc["2026-03", "incremental_revenue_usd"] == pytest.approx(-5 * UPLIFT_EACH / 60)


def test_no_support_lost_when_remaining_agents_have_room():
    r = run({0: 8}, agents=2, terms={2: 1})
    assert r["advertisers_support_lost"].sum() == 0


def test_support_window_basis_scales_revenue():
    r = run({0: 4}, uplift_basis="support_window")
    assert r.loc["2026-01", "incremental_revenue_usd"] == pytest.approx(4 * UPLIFT_EACH * 60 / 365)


def test_revenue_uses_budget_of_each_arrival_day():
    r = run({0: 2, 1: 1}, agents=1, budgets={0: 10_000, 1: 20_000})
    assert r.loc["2026-01", "incremental_revenue_usd"] == pytest.approx((2 * 10_000 + 20_000) * 0.135)


def test_still_waiting_on_december_31_is_not_expired():
    r = run({340: 5}, agents=0)
    assert r.loc["2026-12", "advertisers_waiting"] == 5
    assert r["advertisers_expired"].sum() == 0


def test_lost_uplift_is_prorated_by_each_advertisers_days_left():
    # 10 start day 0 and 10 start day 20; one of 2 agents leaves Mar 1 (day 59), so half
    # of each group is lost, with 1 and 21 support days left respectively.
    r = run({0: 10, 20: 10}, agents=2, terms={2: 1})
    assert r.loc["2026-03", "advertisers_support_lost"] == 10
    assert r.loc["2026-03", "incremental_revenue_usd"] == pytest.approx(
        -(5 * UPLIFT_EACH * 1 / 60 + 5 * UPLIFT_EACH * 21 / 60))


def test_december_termination_strands_advertisers_at_year_end():
    # 20 start Nov 15 (day 318); one of 2 agents leaves Jan 1, 2027 with 13 days of
    # their support left. The loss is booked in December.
    r = run({318: 20}, agents=2, terms={12: 1})
    assert r.loc["2026-12", "advertisers_support_lost"] == 10
    assert r.loc["2026-12", "incremental_revenue_usd"] == pytest.approx(-10 * UPLIFT_EACH * 13 / 60)


def test_december_hire_absorbs_a_december_departure():
    r = run({318: 20}, agents=2, hires={12: 1}, terms={12: 1})
    assert r["advertisers_support_lost"].sum() == 0


def test_december_hire_is_paid_but_never_productive_in_2026():
    r = run({340: 5}, agents=0, hires={12: 1})
    assert r.loc["2026-12", "advertisers_supported"] == 0
    assert r.loc["2026-12", "salary_cost_usd"] == pytest.approx(1_000)


def test_utilization_counts_agents_serving_notice_in_capacity():
    r = run({0: 10}, agents=2, terms={1: 1})
    assert r.loc["2026-01", "utilization"] == pytest.approx(0.5)


def test_hire_and_terminate_in_the_same_month():
    r = run({}, agents=2, hires={1: 1}, terms={1: 1})
    assert r.loc["2026-01", "agents_active"] == 2      # 1 staying + 1 on notice
    assert r.loc["2026-01", "agents_in_training"] == 1
    assert r.loc["2026-01", "salary_cost_usd"] == pytest.approx(3_000)
    assert r.loc["2026-02", "agents_active"] == 2      # 1 staying + 1 former trainee


def test_trainees_cannot_be_terminated():
    with pytest.raises(ValueError, match="productive"):
        run({}, agents=0, hires={1: 1}, terms={1: 1})


def _country_args(**overrides):
    args = dict(daily_arrivals=np.zeros(365), daily_budget=np.full(365, 1e4), agents_start=1,
                hires=[0] * 12, terminations=[0] * 12, annual_salary=SALARY)
    args.update(overrides)
    return args


@pytest.mark.parametrize("overrides, message", [
    (dict(daily_arrivals=np.zeros(364)), "365"),
    (dict(daily_arrivals=np.r_[np.inf, np.zeros(364)]), "daily_arrivals"),
    (dict(daily_arrivals=np.r_[-1.0, np.zeros(364)]), "daily_arrivals"),
    (dict(daily_budget=np.r_[np.nan, np.full(364, 1e4)]), "daily_budget"),
    (dict(daily_budget=np.full(365, -1e4)), "daily_budget"),
    (dict(hires=[0.5] + [0] * 11), "hires"),
    (dict(terminations=[0] * 11), "terminations"),
    (dict(agents_start=652.9), "agents_start"),
    (dict(agents_start=-1), "agents_start"),
    (dict(annual_salary=np.nan), "annual_salary"),
    (dict(uplift_basis="anual"), "uplift_basis"),
])
def test_simulate_country_rejects_invalid_values(overrides, message):
    with pytest.raises(ValueError, match=message):
        simulate_country(**_country_args(**overrides))


# ---- Full runs on the shared sample files (the hand-offs from Roles 1 and 3) ----

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sample"


def load_samples():
    return (pd.read_csv(SAMPLE / "sample_demand.csv"),
            pd.read_csv(SAMPLE / "sample_staffing_plan.csv"),
            pd.read_csv(SAMPLE / "sample_country_parameters.csv"))


def assert_every_signup_accounted_for(out):
    by_country = out.groupby("country")
    december = out[out["month"] == "2026-12"].set_index("country")["advertisers_waiting"]
    accounted = (by_country["advertisers_supported"].sum()
                 + by_country["advertisers_expired"].sum() + december)
    assert np.allclose(accounted, by_country["forecast_eligible"].sum())


def test_simulate_plan_on_samples_matches_results_contract():
    out = simulate_plan(*load_samples())
    validate(out, RESULTS_COLUMNS, "simulate_plan output")
    assert len(out) == 22 * 12
    assert (out["advertisers_waiting"] >= 0).all()


def test_sample_run_accounts_for_every_signup():
    assert_every_signup_accounted_for(simulate_plan(*load_samples()))


def test_tight_staffing_sample_run_exercises_waiting_expiry_and_losses():
    demand, plan, params = load_samples()
    params = params.assign(agents_jan_2026=(params["agents_jan_2026"] * 0.15).astype(int) + 2)
    plan = plan.assign(hires_requested=0,
                       terminations_requested=(plan["month"] == "2026-02").astype(int))
    out = simulate_plan(demand, plan, params)
    validate(out, RESULTS_COLUMNS, "simulate_plan output")
    assert out["advertisers_expired"].sum() > 0
    assert out["advertisers_support_lost"].sum() > 0
    assert (out["advertisers_waiting"] >= 0).all()
    assert (out["utilization"] <= 1 + 1e-9).all()
    assert_every_signup_accounted_for(out)


# ---- Bad inputs must raise, not run silently ----

def _break(table, change):
    demand, plan, params = load_samples()
    tables = {"demand": demand, "plan": plan, "params": params}
    tables[table] = change(tables[table])
    return tables["demand"], tables["plan"], tables["params"]


@pytest.mark.parametrize("table, change, message", [
    ("demand", lambda d: d.replace({"country": {"Spain": "spain "}}), "not in country_parameters"),
    ("demand", lambda d: d[d["country"] != "Spain"], "no demand rows"),
    ("demand", lambda d: pd.concat([d, d.head(1)]), "duplicate"),
    ("demand", lambda d: d.assign(date=d["date"].str.replace("2026", "2025")), "2026"),
    ("demand", lambda d: d.assign(eligible_signups=-d["eligible_signups"] - 1), "daily_arrivals"),
    ("demand", lambda d: d.assign(mean_annual_budget_usd=np.nan), "daily_budget"),
    ("demand", lambda d: d.assign(mean_annual_budget_usd=-d["mean_annual_budget_usd"]), "daily_budget"),
    ("plan", lambda p: p.replace({"month": {"2026-01": "2026-1"}}), "month"),
    ("plan", lambda p: pd.concat([p, p.head(1)]), "duplicate"),
    ("plan", lambda p: p.assign(hires_requested=p["hires_requested"] + 0.5), "whole number"),
    ("plan", lambda p: p.replace({"country": {"UK": "United Kingdom"}}), "not in country_parameters"),
    ("params", lambda c: c.assign(annual_salary_usd=np.nan), "annual_salary"),
    ("params", lambda c: c.assign(agents_jan_2026=c["agents_jan_2026"] + 0.9), "agents_start"),
])
def test_mismatched_inputs_raise_instead_of_running_silently(table, change, message):
    with pytest.raises(ValueError, match=message):
        simulate_plan(*_break(table, change))


def test_missing_budget_on_a_day_with_no_signups_is_allowed():
    demand, plan, params = load_samples()
    demand.loc[demand["eligible_signups"] == 0, "mean_annual_budget_usd"] = np.nan
    demand.loc[0, ["eligible_signups", "mean_annual_budget_usd"]] = [0, np.nan]
    out = simulate_plan(demand, plan, params)
    assert out["incremental_revenue_usd"].notna().all()


def test_value_errors_from_simulate_plan_name_the_country():
    demand, plan, params = load_samples()
    params = params.astype({"agents_jan_2026": float})
    params.loc[params["country"] == "USA", "agents_jan_2026"] = 652.9
    with pytest.raises(ValueError, match="USA"):
        simulate_plan(demand, plan, params)
