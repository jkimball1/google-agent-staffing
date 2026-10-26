# Staffing optimizer and scenarios: integration guide

Owner: Mer McFadden (Role 3). Decisions: `docs/assumptions.md` (D4, D8). The simulator it relies on is described in `src/simulation/README.md`.

## Get the recommended plan

```python
from src.optimization.scenarios import recommended_plan

plan_df, results_df = recommended_plan()
```

- **Inputs:** loaded by `load_inputs()`. It uses Role 1's `forecast_demand` and `load_country_parameters` on the course workbook. **Until `forecast_demand` is implemented, it falls back to `data/sample/` with a warning.** The sample demand is 2025 sign-ups replayed as 2026, so it is not a forecast.
- **Output:** `plan_df` has `STAFFING_PLAN_COLUMNS` (264 rows). `results_df` is the simulator's output for that plan: `RESULTS_COLUMNS` plus `advertisers_support_lost`, 264 rows.
- **Speed:** about 40 s for 22 countries. The result is cached, so `run_scenario`, `sensitivity_table`, `write_outputs` and repeated calls reuse it. Call `clear_cache()` after the forecast changes.
- **Save the final files:** `python -m src.optimization.optimizer` writes `outputs/plan_2026.csv` (results) and `outputs/staffing_plan_2026.csv` (hires and terminations). Run it once the real forecast is in. Don't commit CSVs made from the sample data.

To optimize other inputs directly:

```python
from src.optimization.optimizer import optimize_staffing

plan_df, results_df = optimize_staffing(demand_df, country_parameters_df)
# optional: simulate_fn=..., uplift_basis="support_window", year_end_floor=True
```

## Scenarios (used by the GenAI assistant)

```python
from src.optimization.scenarios import run_scenario, sensitivity_table

run_scenario(demand_multiplier=1.2, country="Germany")  # results_df, all 22 countries
sensitivity_table()                                     # one row each for -20%, baseline, +20%
```

| Function | What changes | Answers |
|---|---|---|
| `run_scenario(m, country)` | Demand × `m` for `country` (or every country if `None`). **That country's plan is re-optimized.** Other countries keep the recommended plan. | "What should we do if sign-ups rise 20% in Germany?" |
| `sensitivity_table(multipliers)` | Demand × each multiplier for every country. **The recommended plan stays fixed.** | "How does our plan hold up if demand is 20% off?" (notebook section 5) |

- `country` matching ignores capitalization. An unknown country, or a multiplier that is negative or not a number, raises `ValueError`.
- One-country scenarios take about 2 s. All-country scenarios take about 40 s. Both are cached by (multiplier, country).
- `sensitivity_table` returns all-country yearly totals: eligible sign-ups, supported, expired, waiting on Dec 31, support lost, hires, terminations, revenue, cost and net value.

## How the search works

Countries don't share agents (D6), so each country is planned separately by `optimize_country(daily_arrivals, daily_budget, agents_start, annual_salary, uplift_basis="annual", year_end_floor=False)`, which returns 12 hires and 12 terminations.

1. **Plan shape.** A plan is the productive headcount wanted after each month's decision (from Feb 1, 2026 through Jan 1, 2027). Raising it means hiring that month, and lowering it means giving notice. Every non-negative path is a valid plan. Plans never hire and terminate in the same month.
2. **Start.** The best of three plans: keep the starting staff; a demand-based plan with enough agents to hold everyone who arrived in the previous 60 days, at each month's busiest day; and 80% of that.
3. **Local search.** Move one month's headcount, or every month from there on, up or down by a step. Keep any move that raises the country's 2026 net value, scored with `simulate_country`. Steps halve down to 1 agent.

This is a heuristic, so the result isn't guaranteed to be the best possible plan. It is never worse than keeping the starting staff, since that is one of the starting candidates. On the sample data, a version that runs the full search from all three starts found plans worth 0.25% more in total ($477.6M vs $476.5M) but took three times as long, so the faster version is used. Individual countries can be further off. For example, under the 60-day basis the USA plan is about $0.4M short of the plan found for the annual basis.

## Behavior to know about

| Situation | What happens |
|---|---|
| Country where agents cost more than they earn | Staff are cut, even if sign-ups then expire. Each agent supports about 60 advertisers a year (10 at a time × 60 days), worth 60 × 13.5% × the mean budget. Below the salary, serving loses money. |
| Waiting | Uplift counts as long as an advertiser is assigned within 60 days, so waiting costs nothing in this model. The plan uses the line as a buffer and can run fewer agents than "no one waits" would need. `average_wait_days` reports the cost to advertisers. |
| Year end (D8) | Only 2026 is counted. Hiring in December, or for demand arriving late in the year, mostly pays off in 2027, so the plan tends to under-prepare for January 2027. `year_end_floor=True` requires enough agents on Jan 1, 2027 to hold everyone still in support. It is off by default because in unprofitable countries it forces hires that lose money. |
| `uplift_basis="support_window"` | Revenue per advertiser drops to 60/365 of the annual figure, so countries with low budgets relative to salaries are cut back. The search optimizes for whichever basis is passed (D4 sensitivity). |
| Invalid inputs | The simulator's checks run before the search. Errors from `optimize_staffing` name the country. |

## Tests

`python -m pytest -q tests/test_optimization.py` runs 21 tests (under a minute):
- hand-checkable `optimize_country` cases: no demand, demand that starts in July, unprofitable demand, overstaffing, the 60-day revenue basis, the year-end floor and invalid inputs
- `optimize_staffing` on two sample countries: valid plan, beats doing nothing, matches per-country results, evaluates with `simulate_fn`
- scenarios called exactly the way `src/genai/assistant.py` calls them, plus the sensitivity table, caching, `write_outputs` and the sample-data fallback
