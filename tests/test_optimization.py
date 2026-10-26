"""Tests for the staffing optimizer and scenarios (Role 3).

Small synthetic cases check the search behaves sensibly. Sample-data runs use two
countries to keep the suite fast.
"""

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.optimization import scenarios
from src.optimization.optimizer import optimize_country, optimize_staffing, year_end_need
from src.schemas import RESULTS_COLUMNS, STAFFING_PLAN_COLUMNS, validate
from src.simulation.simulator import daily_inputs, simulate_country, simulate_plan

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "sample"
TWO = ["Spain", "Vietnam"]  # one overstaffed, one understaffed in the sample data


def net(arrivals, budget, start, hires, terms, salary, basis="annual"):
    return simulate_country(arrivals, budget, start, hires, terms, salary, basis)["net_value_usd"].sum()


def final_level(start, hires, terms):
    return start + sum(hires) - sum(terms)


def assert_valid_plan(hires, terms):
    assert len(hires) == len(terms) == 12
    for h, x in zip(hires, terms):
        assert h >= 0 and x >= 0 and h == int(h) and x == int(x)
        assert h == 0 or x == 0, "never hire and terminate in the same month"


@pytest.fixture(scope="module")
def sample_two():
    demand = pd.read_csv(SAMPLE / "sample_demand.csv")
    params = pd.read_csv(SAMPLE / "sample_country_parameters.csv")
    return demand[demand["country"].isin(TWO)], params[params["country"].isin(TWO)]


# --- optimize_country: hand-checkable cases ---------------------------------------

def test_no_demand_terminates_everyone_in_january():
    # Keeping an agent all year costs a full salary; terminating in January costs
    # one month's salary plus 40%. With nothing to do, cut everyone at once.
    hires, terms = optimize_country(np.zeros(365), np.zeros(365), 50, 12_000)
    assert_valid_plan(hires, terms)
    assert terms[0] == 50 and sum(terms) == 50 and sum(hires) == 0


def test_profitable_demand_from_july_hires_no_earlier_than_june():
    # No agents and no demand until July 1, then 3 sign-ups a day worth far more
    # than an agent costs. Hiring before June only adds salary.
    arrivals = np.zeros(365)
    arrivals[181:] = 3.0
    budget = np.full(365, 100_000.0)
    hires, terms = optimize_country(arrivals, budget, 0, 12_000)
    assert_valid_plan(hires, terms)
    assert sum(hires[:5]) == 0
    assert sum(hires) > 0
    result = simulate_country(arrivals, budget, 0, hires, terms, 12_000)
    assert result["advertisers_expired"].sum() < 1e-6


def test_unprofitable_demand_is_not_staffed():
    # Each agent can serve about 60 advertisers a year; at a $100 budget that is
    # 60 x 13.5% x $100 = $810 of uplift against a $12,000 salary.
    arrivals = np.full(365, 2.0)
    hires, terms = optimize_country(arrivals, np.full(365, 100.0), 20, 12_000)
    assert final_level(20, hires, terms) == 0
    assert terms[0] == 20


def test_never_worse_than_keeping_the_starting_staff():
    rng = np.random.default_rng(0)
    arrivals = rng.poisson(4, 365).astype(float)
    budget = np.full(365, 20_000.0)
    hires, terms = optimize_country(arrivals, budget, 30, 40_000)
    assert net(arrivals, budget, 30, hires, terms, 40_000) >= net(
        arrivals, budget, 30, [0] * 12, [0] * 12, 40_000)


def test_overstaffed_country_cuts_staff_early():
    # 2 sign-ups a day need about 12 agents (2 x 60 days / 10); 100 are employed.
    arrivals = np.full(365, 2.0)
    budget = np.full(365, 50_000.0)
    hires, terms = optimize_country(arrivals, budget, 100, 30_000)
    assert_valid_plan(hires, terms)
    assert terms[0] >= 80
    assert 10 <= final_level(100, hires, terms) <= 16


def test_support_window_basis_is_used_in_the_search():
    # Annual basis: 60 x 13.5% x $5,000 = $40,500 of uplift per agent-year beats a
    # $30,000 salary. The 60-day basis cuts that to about $6,700, so staff go.
    arrivals = np.full(365, 2.0)
    budget = np.full(365, 5_000.0)
    _, terms_annual = optimize_country(arrivals, budget, 12, 30_000, uplift_basis="annual")
    h, terms_window = optimize_country(arrivals, budget, 12, 30_000, uplift_basis="support_window")
    assert final_level(12, h, terms_window) == 0
    assert sum(terms_window) > sum(terms_annual)


def test_year_end_need_counts_advertisers_still_in_support():
    arrivals = np.zeros(365)
    arrivals[-60:] = 1.0  # 60 advertisers arrive in the last 60 days
    assert year_end_need(arrivals) == 6
    arrivals[-60] = 100.0  # started Nov 2 (day 305), graduates on Jan 1, 2027
    assert year_end_need(arrivals) == 6
    arrivals[-59] = 100.0  # started Nov 3, still in support on Jan 1, 2027
    assert year_end_need(arrivals) == 16


def test_year_end_floor_keeps_enough_agents_for_2027():
    # Demand only in late December at a tiny budget: not worth staffing in 2026,
    # but the optional floor still keeps enough agents to hold them on Jan 1, 2027.
    arrivals = np.zeros(365)
    arrivals[-10:] = 5.0
    budget = np.full(365, 100.0)
    h0, x0 = optimize_country(arrivals, budget, 0, 12_000)
    assert sum(h0) == 0
    h1, x1 = optimize_country(arrivals, budget, 0, 12_000, year_end_floor=True)
    assert_valid_plan(h1, x1)
    assert final_level(0, h1, x1) >= year_end_need(arrivals) == 5


def test_rejects_invalid_country_inputs():
    with pytest.raises(ValueError):
        optimize_country(np.zeros(365), np.zeros(365), -1, 12_000)
    with pytest.raises(ValueError):
        optimize_country(np.zeros(364), np.zeros(365), 5, 12_000)


# --- optimize_staffing: the full-plan entry point ---------------------------------

def test_optimize_staffing_returns_a_plan_and_its_results(sample_two):
    demand, params = sample_two
    plan, results = optimize_staffing(demand, params, simulate_plan)
    validate(plan, STAFFING_PLAN_COLUMNS, "plan")
    validate(results, RESULTS_COLUMNS, "results")
    assert len(plan) == len(results) == 24
    for c in TWO:
        p = plan[plan["country"] == c]
        assert_valid_plan(list(p["hires_requested"]), list(p["terminations_requested"]))
    pd.testing.assert_frame_equal(results, simulate_plan(demand, plan, params))


def test_optimize_staffing_beats_doing_nothing_per_country(sample_two):
    demand, params = sample_two
    _, results = optimize_staffing(demand, params, simulate_plan)
    nothing = simulate_plan(demand, pd.DataFrame(columns=STAFFING_PLAN_COLUMNS), params)
    best = results.groupby("country")["net_value_usd"].sum()
    base = nothing.groupby("country")["net_value_usd"].sum()
    assert (best >= base - 1e-6).all()


def test_optimize_staffing_evaluates_with_simulate_fn(sample_two):
    demand, params = sample_two
    calls = []

    def stand_in(d, p, c):
        calls.append(p)
        return simulate_plan(d, p, c)

    plan, _ = optimize_staffing(demand, params, stand_in)
    assert len(calls) == 1
    pd.testing.assert_frame_equal(calls[0], plan)


def test_optimize_staffing_matches_optimize_country(sample_two):
    demand, params = sample_two
    plan, _ = optimize_staffing(demand, params, simulate_plan)
    row = params[params["country"] == "Vietnam"].iloc[0]
    arrivals, budget = daily_inputs(demand, "Vietnam")
    hires, terms = optimize_country(arrivals, budget, row.agents_jan_2026, row.annual_salary_usd)
    p = plan[plan["country"] == "Vietnam"]
    assert list(p["hires_requested"]) == hires
    assert list(p["terminations_requested"]) == terms


# --- scenarios ------------------------------------------------------------------

@pytest.fixture
def small_inputs(sample_two, monkeypatch):
    monkeypatch.setattr(scenarios, "load_inputs", lambda: sample_two)
    scenarios.clear_cache()
    yield sample_two
    scenarios.clear_cache()


def test_run_scenario_baseline_is_the_recommended_plan(small_inputs):
    demand, params = small_inputs
    _, expected = optimize_staffing(demand, params, simulate_plan)
    pd.testing.assert_frame_equal(scenarios.run_scenario(), expected)


def test_run_scenario_as_the_assistant_calls_it(small_inputs):
    # src/genai/assistant.py calls run_scenario(demand_multiplier=..., country=...)
    # and matches the country name case-insensitively.
    base = scenarios.run_scenario(demand_multiplier=1.0, country="vietnam")
    up = scenarios.run_scenario(demand_multiplier=1.2, country="vietnam")
    validate(up, RESULTS_COLUMNS, "scenario")
    assert len(up) == 24
    v_up = up[up["country"] == "Vietnam"]["forecast_eligible"].sum()
    v_base = base[base["country"] == "Vietnam"]["forecast_eligible"].sum()
    assert v_up == pytest.approx(1.2 * v_base)
    # Other countries keep their baseline demand and plan.
    pd.testing.assert_frame_equal(
        up[up["country"] == "Spain"].reset_index(drop=True),
        base[base["country"] == "Spain"].reset_index(drop=True))


def test_run_scenario_reoptimizes_for_the_new_demand(small_inputs):
    demand, params = small_inputs
    up = scenarios.run_scenario(demand_multiplier=1.5)
    scaled = demand.assign(eligible_signups=demand["eligible_signups"] * 1.5)
    _, expected = optimize_staffing(scaled, params, simulate_plan)
    pd.testing.assert_frame_equal(up, expected)


def test_run_scenario_rejects_bad_requests(small_inputs):
    with pytest.raises(ValueError, match="Atlantis"):
        scenarios.run_scenario(1.2, country="Atlantis")
    with pytest.raises(ValueError):
        scenarios.run_scenario(-0.5)
    with pytest.raises(ValueError):
        scenarios.run_scenario(math.nan)


def test_sensitivity_table_keeps_the_baseline_plan_fixed(small_inputs):
    demand, params = small_inputs
    table = scenarios.sensitivity_table()
    assert list(table["demand_multiplier"]) == [0.8, 1.0, 1.2]
    base = scenarios.run_scenario()
    row = table.set_index("demand_multiplier").loc[1.0]
    assert row["net_value_usd"] == pytest.approx(base["net_value_usd"].sum())
    assert row["eligible_signups"] == pytest.approx(base["forecast_eligible"].sum())
    # Same plan at every demand level, so hiring and terminations don't change.
    assert table["agents_hired"].nunique() == 1
    assert table["agents_terminated"].nunique() == 1
    assert table["eligible_signups"].is_monotonic_increasing
    assert table["advertisers_expired"].is_monotonic_increasing


def test_load_inputs_falls_back_to_samples_until_the_forecast_exists(monkeypatch):
    def not_yet(*args):
        raise NotImplementedError

    monkeypatch.setattr(scenarios.forecast, "forecast_demand", not_yet)
    monkeypatch.setattr(scenarios.forecast, "load_country_parameters", not_yet)
    scenarios.clear_cache()
    with pytest.warns(UserWarning, match="sample"):
        demand, params = scenarios.load_inputs()
    assert len(params) == 22
    assert set(demand["country"]) == set(params["country"])


def test_recommended_plan_is_computed_once_and_shared(small_inputs, monkeypatch):
    plan, results = scenarios.recommended_plan()
    validate(plan, STAFFING_PLAN_COLUMNS, "plan")
    monkeypatch.setattr(scenarios, "optimize_staffing", None)  # would fail if called again
    again_plan, again_results = scenarios.recommended_plan()
    pd.testing.assert_frame_equal(again_plan, plan)
    pd.testing.assert_frame_equal(scenarios.run_scenario(), results)


def test_write_outputs_saves_the_recommended_plan(small_inputs, tmp_path):
    results_path, plan_path = scenarios.write_outputs(tmp_path)
    plan, results = scenarios.recommended_plan()
    pd.testing.assert_frame_equal(pd.read_csv(results_path), results, check_dtype=False)
    pd.testing.assert_frame_equal(pd.read_csv(plan_path), plan, check_dtype=False)


def test_scenarios_accept_whole_number_demand_counts(small_inputs, monkeypatch):
    # A forecast may return integer counts; scaling them must not fail.
    demand, params = small_inputs
    as_ints = demand.assign(eligible_signups=demand["eligible_signups"].round().astype("int64"))
    monkeypatch.setattr(scenarios, "load_inputs", lambda: (as_ints, params))
    scenarios.clear_cache()
    up = scenarios.run_scenario(1.2, country="Spain")
    assert up[up["country"] == "Spain"]["forecast_eligible"].sum() == pytest.approx(
        1.2 * as_ints[as_ints["country"] == "Spain"]["eligible_signups"].sum())


def test_load_inputs_returns_copies(sample_two, monkeypatch):
    monkeypatch.setattr(scenarios.forecast, "forecast_demand", lambda path: sample_two[0])
    monkeypatch.setattr(scenarios.forecast, "load_country_parameters", lambda path: sample_two[1])
    scenarios.clear_cache()
    demand, _ = scenarios.load_inputs()
    total = demand["eligible_signups"].sum()
    demand["eligible_signups"] *= 2  # a notebook cell editing its copy in place
    assert scenarios.load_inputs()[0]["eligible_signups"].sum() == pytest.approx(total)
    scenarios.clear_cache()
