# Interfaces

These are the contracts between modules. As long as your inputs and outputs match them, you can organize your own code however you like and build without waiting for anyone else.

Column lists live in code in [`src/schemas.py`](src/schemas.py). Use `validate(df, COLUMNS)` to check your output. **To change a contract**, edit both this file and `src/schemas.py` in one PR and tag the people whose modules consume it.

## Pipeline

```
workbook ──► forecast_demand() ──► demand_df ─┐
         └─► load_country_parameters() ───────┼─► optimize_staffing(simulate_fn=simulate_plan)
                                               │        │
                                               │        ▼
                                               │   results_df ──► outputs/plan_2026.csv
                                               │        │
                              run_scenario(multiplier, country) ◄── answer_question()
```

## Functions

| Owner | Function | Returns |
|---|---|---|
| Member 1 | `src.forecasting.forecast.forecast_demand(workbook_path)` | `demand_df` |
| Member 1 | `src.forecasting.forecast.load_country_parameters(workbook_path)` | `country_parameters_df` |
| Member 2 | `src.simulation.simulator.simulate_plan(demand_df, staffing_plan_df, country_parameters_df)` | `results_df` |
| Member 3 | `src.optimization.optimizer.optimize_staffing(demand_df, country_parameters_df, simulate_fn)` | `(recommended_plan_df, results_df)` |
| Member 3 | `src.optimization.scenarios.run_scenario(demand_multiplier=1.0, country=None)` | `results_df` |
| Member 4 | `src.genai.assistant.answer_question(question, planning_model)` | `StaffingMemo` (Pydantic) |

## Data formats

All sample files in `data/sample/` are **synthetic**. Regenerate them with `python data/sample/make_samples.py`.

### `demand_df`: one row per country per day of 2026 (sample: `sample_demand.csv`)

| Column | Type | Meaning |
|---|---|---|
| `country` | str | Country name, as in the workbook |
| `date` | `YYYY-MM-DD` | 2026-01-01 … 2026-12-31 |
| `eligible_signups` | float ≥ 0 | Expected eligible advertiser arrivals that day |
| `mean_annual_budget_usd` | float ≥ 0 | Mean annual budget of those arrivals (for revenue) |

### `country_parameters_df`: one row per country (sample: `sample_country_parameters.csv`)

| Column | Type | Meaning |
|---|---|---|
| `country` | str | |
| `annual_salary_usd` | float | Per agent |
| `eligibility_threshold_usd` | float | Minimum annual budget to qualify for support |
| `agents_jan_2026` | int | Starting headcount (January 2026, from workbook) |

### `staffing_plan_df`: one row per country per month (sample: `sample_staffing_plan.csv`)

| Column | Type | Meaning |
|---|---|---|
| `country` | str | |
| `month` | `YYYY-MM` | 2026-01 … 2026-12 |
| `hires_requested` | int ≥ 0 | Hired at start of month, productive from next month |
| `terminations_requested` | int ≥ 0 | Notice given at start of month, gone from next month |

### `results_df`: one row per country per month (sample: `sample_results.csv`)

The final plan is this table for all 22 countries × 12 months = **264 rows**, saved as `outputs/plan_2026.csv`.

| Column | Meaning |
|---|---|
| `country`, `month` | Keys |
| `forecast_eligible` | Eligible arrivals that month |
| `agents_active` | Productive agents (excludes trainees) |
| `agents_in_training` | Agents in their training month |
| `agents_hired` | Hires decided this month |
| `agents_terminated` | Terminations decided this month |
| `advertisers_supported` | New assignments started this month |
| `advertisers_waiting` | Unassigned at month end |
| `advertisers_expired` | Waited more than 60 days and were lost |
| `average_wait_days` | Mean wait for advertisers assigned this month |
| `utilization` | Occupied slots ÷ (agents_active × 10) |
| `incremental_revenue_usd` | Estimated uplift revenue |
| `salary_cost_usd` | Salary paid this month (incl. trainees and agents serving notice) |
| `termination_cost_usd` | 40% of annual salary per termination |
| `total_cost_usd` | Salary + termination |
| `net_value_usd` | Revenue − total cost |
