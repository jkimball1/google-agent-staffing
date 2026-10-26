"""Member 3 — Sensitivity analysis and the scenario entry point used by the GenAI app.

run_scenario() is the main hook between the planning model and the assistant:
the assistant calls it to compute new numbers instead of describing a static table.

  recommended_plan   the baseline plan and its results, optimized once and cached
  run_scenario       re-optimizes the plan for the scaled demand ("what should we do?")
  sensitivity_table  keeps the recommended plan fixed and re-simulates it at each demand
                     level ("how robust is our plan?"); this is notebook section 5

Inputs come from Role 1's forecast. Until forecast_demand is implemented, the sample
files in data/sample/ are used instead, with a warning.
"""

import math
import warnings
from pathlib import Path

import pandas as pd

from src.forecasting import forecast
from src.optimization.optimizer import optimize_staffing
from src.schemas import STAFFING_PLAN_COLUMNS
from src.simulation.simulator import simulate_plan

ROOT = Path(__file__).resolve().parents[2]
WORKBOOK = ROOT / "data" / "raw" / "DADS5250_Hackathon_Google_Data.xlsx"
SAMPLE = ROOT / "data" / "sample"

_cache = {}


def clear_cache():
    """Forget loaded inputs and optimized plans (e.g. after the forecast changes)."""
    _cache.clear()


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    """(demand_df, country_parameters_df) from Role 1, or the samples until that exists."""
    if "inputs" not in _cache:
        try:
            inputs = (forecast.forecast_demand(str(WORKBOOK)),
                      forecast.load_country_parameters(str(WORKBOOK)))
        except NotImplementedError:
            warnings.warn("forecast_demand isn't implemented yet; using the sample data in "
                          "data/sample/ (2025 sign-ups replayed as 2026), not a forecast",
                          UserWarning, stacklevel=2)
            inputs = (pd.read_csv(SAMPLE / "sample_demand.csv"),
                      pd.read_csv(SAMPLE / "sample_country_parameters.csv"))
        _cache["inputs"] = inputs
    return _cache["inputs"]


def recommended_plan() -> tuple[pd.DataFrame, pd.DataFrame]:
    """(recommended_plan_df, results_df) for the baseline forecast.

    Optimized once (about 40 s for 22 countries) and reused by run_scenario,
    sensitivity_table, write_outputs and the notebook. Returns copies."""
    if "baseline" not in _cache:
        demand, params = load_inputs()
        _cache["baseline"] = optimize_staffing(demand, params, simulate_plan)
    plan, results = _cache["baseline"]
    return plan.copy(), results.copy()


def _scaled(demand, multiplier, countries):
    rows = demand["country"].isin(countries)
    out = demand.copy()
    out.loc[rows, "eligible_signups"] = out.loc[rows, "eligible_signups"] * multiplier
    return out


def run_scenario(demand_multiplier: float = 1.0, country: str | None = None) -> pd.DataFrame:
    """Re-run the pipeline with demand scaled by `demand_multiplier`.

    If `country` is given (any capitalization), only that country's demand is scaled and
    only its plan is re-optimized; every other country keeps the recommended plan.
    Returns RESULTS_COLUMNS for all countries and months.
    """
    if not math.isfinite(demand_multiplier) or demand_multiplier < 0:
        raise ValueError(f"demand_multiplier must be a finite number >= 0, got {demand_multiplier!r}")
    demand, params = load_inputs()
    countries = list(params["country"])
    if country is not None:
        match = [c for c in countries if c.casefold() == country.strip().casefold()]
        if not match:
            raise ValueError(f"unknown country {country!r}; expected one of {countries}")
        countries = match

    key = ("scenario", float(demand_multiplier), tuple(countries))
    if key not in _cache:
        base_plan, base_results = recommended_plan()
        if demand_multiplier == 1.0:
            _cache[key] = base_results
        else:
            scaled = _scaled(demand, demand_multiplier, countries)
            in_scope = params["country"].isin(countries)
            new_plan, _ = optimize_staffing(scaled[scaled["country"].isin(countries)],
                                            params[in_scope], simulate_plan)
            plan = pd.concat([base_plan[~base_plan["country"].isin(countries)], new_plan])
            _cache[key] = simulate_plan(scaled, plan, params)
    return _cache[key].copy()


def sensitivity_table(multipliers=(0.8, 1.0, 1.2)) -> pd.DataFrame:
    """Compare the recommended plan under each demand multiplier (the +/-20% analysis).

    The plan stays fixed at the baseline recommendation; only demand changes. One row
    per multiplier with all-country totals for the year.
    """
    demand, params = load_inputs()
    plan, _ = recommended_plan()
    rows = []
    for mult in multipliers:
        r = simulate_plan(_scaled(demand, mult, list(params["country"])), plan, params)
        dec = r[r["month"] == "2026-12"]
        rows.append({
            "demand_multiplier": mult,
            "eligible_signups": r["forecast_eligible"].sum(),
            "advertisers_supported": r["advertisers_supported"].sum(),
            "advertisers_expired": r["advertisers_expired"].sum(),
            "advertisers_waiting_dec_31": dec["advertisers_waiting"].sum(),
            "advertisers_support_lost": r["advertisers_support_lost"].sum(),
            "agents_hired": int(r["agents_hired"].sum()),
            "agents_terminated": int(r["agents_terminated"].sum()),
            "incremental_revenue_usd": r["incremental_revenue_usd"].sum(),
            "total_cost_usd": r["total_cost_usd"].sum(),
            "net_value_usd": r["net_value_usd"].sum(),
        })
    return pd.DataFrame(rows)


def write_outputs(out_dir=ROOT / "outputs") -> list[Path]:
    """Save the recommended plan and its results: plan_2026.csv (RESULTS_COLUMNS, 264
    rows) and staffing_plan_2026.csv (STAFFING_PLAN_COLUMNS)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    plan, results = recommended_plan()
    paths = [out_dir / "plan_2026.csv", out_dir / "staffing_plan_2026.csv"]
    results.to_csv(paths[0], index=False)
    plan[STAFFING_PLAN_COLUMNS].to_csv(paths[1], index=False)
    return paths
