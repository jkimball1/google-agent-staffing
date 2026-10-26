"""End-to-end check that the optimizer, scenarios and simulator fit together on all
22 countries, called the way the notebook and the GenAI assistant call them.

Uses Role 1's forecast once it exists, the sample data until then. Takes about 1.5 min.
"""

import warnings

import numpy as np
import pandas as pd
import pytest

from src.optimization import scenarios
from src.schemas import RESULTS_COLUMNS, STAFFING_PLAN_COLUMNS, validate
from src.simulation.simulator import EXTRA_COLUMNS, simulate_plan


@pytest.fixture(scope="module")
def pipeline():
    scenarios.clear_cache()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # the sample-data fallback warning
        demand, params = scenarios.load_inputs()
        plan, results = scenarios.recommended_plan()
    yield demand, params, plan, results
    scenarios.clear_cache()


def by_key(df):
    return df.set_index(["country", "month"]).sort_index()


def test_plan_and_results_follow_the_contracts(pipeline):
    demand, params, plan, results = pipeline
    validate(plan, STAFFING_PLAN_COLUMNS, "plan")
    assert list(results.columns) == RESULTS_COLUMNS + EXTRA_COLUMNS
    assert len(plan) == len(results) == 12 * len(params)
    assert not results.duplicated(["country", "month"]).any()
    assert set(results["country"]) == set(params["country"])
    assert plan["hires_requested"].dtype.kind == plan["terminations_requested"].dtype.kind == "i"
    assert (plan[["hires_requested", "terminations_requested"]] >= 0).all().all()
    assert ((plan["hires_requested"] == 0) | (plan["terminations_requested"] == 0)).all()


def test_simulator_reproduces_the_optimizers_results(pipeline):
    demand, params, plan, results = pipeline
    pd.testing.assert_frame_equal(simulate_plan(demand, plan, params).reset_index(drop=True),
                                  results.reset_index(drop=True))


def test_bookkeeping_holds_on_the_recommended_plan(pipeline):
    demand, params, plan, results = pipeline
    g = results.groupby("country")
    dec = results[results["month"] == "2026-12"].set_index("country")
    accounted = (g["advertisers_supported"].sum() + g["advertisers_expired"].sum()
                 + dec["advertisers_waiting"])
    np.testing.assert_allclose(accounted, g["forecast_eligible"].sum(), atol=1e-6)
    assert results["forecast_eligible"].sum() == pytest.approx(demand["eligible_signups"].sum())
    assert results["utilization"].between(0, 1 + 1e-9).all()
    r, p = by_key(results), by_key(plan)
    assert (r["agents_hired"] == p["hires_requested"]).all()
    assert (r["agents_terminated"] == p["terminations_requested"]).all()
    jan = results[results["month"] == "2026-01"].set_index("country")["agents_active"]
    start = params.set_index("country")["agents_jan_2026"]
    assert (jan == start.loc[jan.index]).all()


def test_recommended_plan_beats_keeping_the_starting_staff(pipeline):
    demand, params, plan, results = pipeline
    nothing = simulate_plan(demand, pd.DataFrame(columns=STAFFING_PLAN_COLUMNS), params)
    gain = (results.groupby("country")["net_value_usd"].sum()
            - nothing.groupby("country")["net_value_usd"].sum())
    assert (gain >= -1e-6).all()


def test_one_country_scenario_as_the_assistant_calls_it(pipeline):
    demand, params, plan, results = pipeline
    country = params["country"].iloc[0]
    up = scenarios.run_scenario(demand_multiplier=1.2, country=country.lower())
    validate(up, RESULTS_COLUMNS, "scenario")
    mine, others = up["country"] == country, results["country"] != country
    assert up.loc[mine, "forecast_eligible"].sum() == pytest.approx(
        1.2 * results.loc[~others, "forecast_eligible"].sum())
    pd.testing.assert_frame_equal(up[~mine].reset_index(drop=True),
                                  results[others].reset_index(drop=True))
    pd.testing.assert_frame_equal(scenarios.run_scenario(), results)


def test_sensitivity_table_matches_the_simulator(pipeline):
    demand, params, plan, results = pipeline
    sens = scenarios.sensitivity_table().set_index("demand_multiplier")
    assert sens.loc[1.0, "net_value_usd"] == pytest.approx(results["net_value_usd"].sum())
    low = simulate_plan(demand.assign(eligible_signups=demand["eligible_signups"] * 0.8), plan, params)
    assert sens.loc[0.8, "net_value_usd"] == pytest.approx(low["net_value_usd"].sum())


def test_output_files_round_trip(pipeline, tmp_path):
    demand, params, plan, results = pipeline
    results_path, plan_path = scenarios.write_outputs(tmp_path)
    saved = pd.read_csv(results_path)
    validate(saved, RESULTS_COLUMNS, "plan_2026.csv")
    assert len(saved) == len(results)
    resim = simulate_plan(demand, pd.read_csv(plan_path), params)
    np.testing.assert_allclose(resim["net_value_usd"], saved["net_value_usd"])
