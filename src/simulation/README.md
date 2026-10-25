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
  - Demand must already be eligibility-filtered (Role 1).
  - Countries or months missing from the plan count as no hires or terminations.
  - Inputs that don't line up raise one `ValueError` listing every problem (see the table below).
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
| Inputs don't line up | `simulate_plan` raises a `ValueError` for: demand/plan countries not in `country_parameters`, countries with no demand rows, dates not `YYYY-MM-DD` or outside 2026, duplicate (country, date) or (country, month) rows, missing or negative sign-ups, missing budgets on days with sign-ups, plan months other than `2026-01`..`2026-12`, hires/terminations that aren't whole numbers ≥ 0, and missing or negative salary/headcount. `simulate_country` skips these checks for speed. |
| Terminating agents who still have advertisers (D5) | The remaining agents take them over if they have free slots. Otherwise those advertisers show up in `advertisers_support_lost`, and the uplift for the support days they miss is subtracted from `incremental_revenue_usd` that month. |
| Hires | Paid from the month they're hired, productive from the next month. A December hire costs salary and never helps in 2026. |
| Agents serving notice | Paid and counted in `agents_active` for the notice month, but take no new advertisers. Staying agents only take new advertisers if they could hold everyone currently assigned, so the pool keeps room for the departing agents' advertisers. |
| Fractional sign-ups | Allowed. Advertiser counts are decimals; agent counts are whole numbers. |
| Revenue timing | Uplift is booked in the month support starts, even if support runs into 2027. Monthly revenue and net value can be negative. |
| Waiting on Dec 31 | Reported in December's `advertisers_waiting`. Not counted as expired. |
| Year-end horizon | Only 2026 salary and revenue are counted. A termination's savings stop on Dec 31, so late-year cuts look worse than they would over a 12-month view, and plans tend to end the year with extra agents. How to handle this is an objective choice (D8) for the optimizer, e.g. note it as a limitation or credit savings beyond December. |

## Tests

`python -m pytest -q tests/test_simulation.py` runs 32 tests: 17 small cases you can check by hand, 4 full-sample runs (results format, every sign-up accounted for, a tightly staffed run that forces waiting, expiries and lost support, and missing budgets on zero-sign-up days), and 11 bad inputs that must raise.
