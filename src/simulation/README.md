# Staffing simulator: integration guide

Owner: Mer McFadden (Role 2). Rules and decisions: `docs/assumptions.md` (D3, D5, D6).

## Evaluate a full plan (all countries)

```python
from src.simulation.simulator import simulate_plan

results = simulate_plan(demand_df, staffing_plan_df, country_parameters_df)
# optional: uplift_basis="support_window" for the 60-day revenue comparison (D4)
```

- **Inputs:** `DEMAND_COLUMNS`, `STAFFING_PLAN_COLUMNS` and `COUNTRY_PARAMETERS_COLUMNS` (see `INTERFACES.md`).
  - Days missing from demand count as zero sign-ups.
  - Months missing from the plan count as no hires or terminations.
  - Demand outside 2026 is ignored.
- **Output:** 264 rows (22 countries × 12 months) with `RESULTS_COLUMNS`, plus one extra column, `advertisers_support_lost`. This is ready to save as `outputs/plan_2026.csv`.
- **Speed:** about 0.1 s for all 22 countries.

## Evaluate one country (faster inside an optimizer)

```python
from src.simulation.simulator import simulate_country

monthly = simulate_country(
    daily_arrivals,      # length-365 array, eligible sign-ups per day of 2026
    daily_budget,        # length-365 array, mean annual budget of those sign-ups
    agents_start,        # January 2026 headcount
    hires,               # 12 ints, decided on the 1st of each month
    terminations,        # 12 ints, notice given on the 1st of each month
    annual_salary,
    uplift_basis="annual",
)
# -> 12 rows indexed "2026-01".."2026-12"; same metric columns, no country/month
```

Countries don't interact (D6), so a plan's total value is the sum of each country's `net_value_usd`. An optimizer can search each country separately.

## Behavior to know about

| Situation | What happens |
|---|---|
| Terminations exceed the productive agents employed that month | `ValueError`. The optimizer should never propose this. |
| Terminating agents who still have advertisers (D5) | The remaining agents take them over if they have free slots. Otherwise those advertisers show up in `advertisers_support_lost` and their uplift is subtracted from `incremental_revenue_usd` that month, so revenue can be negative. |
| Hires | Paid from the month they're hired, productive from the next month. A December hire costs salary and never helps in 2026. |
| Agents serving notice | Paid and counted in `agents_active` for the notice month, but take no new advertisers. |
| Fractional sign-ups | Allowed. Advertiser counts are decimals; agent counts are whole numbers. |
| Revenue timing | Uplift is booked in the month support starts, even if support runs into 2027. |
| Waiting on Dec 31 | Reported in December's `advertisers_waiting`. Not counted as expired. |

## Tests

`python -m pytest -q tests/test_simulation.py` runs 13 small cases you can check by hand, plus a full-sample check against the results format.
