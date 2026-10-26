# Notebook sections 4 and 5: Staffing optimization and sensitivity (draft for integration)

Author: Mer McFadden (Role 3). For whoever assembles `notebooks/final_submission.ipynb` to paste in.
Each block below is marked **[markdown cell]** or **[code cell]**. The code cells assume the
notebook's setup cell has already put the repo root on `sys.path` and defined `ROOT`. They load
their own inputs with `load_inputs()`, which calls Role 1's forecast (or the sample data until the
forecast exists), so they don't need variables from section 2. The first code cell takes about
40 s; later cells reuse its result. Section 5's second code cell takes another 40 s. Text for the
README, sections 7 and 8, and the video is at the end. See `docs/notebook/README.md` for the format.

The markdown deliberately avoids quoting numbers, because they change when the final forecast
lands. Every number is printed by a code cell.

---

**[markdown cell]**

## 4. Staffing optimization: the 2026 plan *(Mer McFadden)*

**Goal (D8):** choose monthly hires and terminations for each country that maximize 2026 net
value: revenue uplift from supported advertisers minus salaries and termination costs. Countries
don't share agents (D6), so each country is planned on its own.

**How the plan is found** (`src/optimization/optimizer.py`)
1. **Plan shape.** For each country, a plan is the productive headcount wanted after each month's
   decision. Raising it means hiring that month (productive the next month); lowering it means
   giving notice that month (leaving the next month).
2. **Starting point.** The best of three simple plans: keep the starting staff; a demand-based
   plan with enough agents to hold everyone who signed up in the previous 60 days; and a leaner
   version of it (80%).
3. **Local search.** Repeatedly move one month's headcount, or every month from there on, up or
   down by a step. Keep any move that raises net value as scored by the simulator (section 3).
   Steps shrink from large to a single agent.

This is a heuristic, so it isn't guaranteed to find the best possible plan. Because "keep the
starting staff" is one of its starting points, it is never worse than doing nothing.

**What drives the answer.** An agent supports about 60 advertisers a year (10 at a time for 60 days
each), worth about 60 × 13.5% × the mean annual budget. Where that is well above the salary,
staffing to serve every sign-up pays; where it is below, the plan cuts staff even if sign-ups expire.

---

**[code cell]**

```python
import pandas as pd
from src.optimization.scenarios import load_inputs, recommended_plan
from src.schemas import STAFFING_PLAN_COLUMNS
from src.simulation.simulator import simulate_plan

demand_df, country_parameters_df = load_inputs()
plan_df, results_df = recommended_plan()  # about 40 s; cached afterwards

# For comparison: keep the January 2026 headcount all year, with no hires or terminations.
keep_staff = simulate_plan(demand_df, pd.DataFrame(columns=STAFFING_PLAN_COLUMNS),
                           country_parameters_df)


def yearly(results):
    g = results.groupby("country")
    wait = (results["average_wait_days"] * results["advertisers_supported"]).groupby(results["country"]).sum()
    return pd.DataFrame({
        "supported": g["advertisers_supported"].sum(),
        "expired": g["advertisers_expired"].sum(),
        "avg_wait_days": wait / g["advertisers_supported"].sum(),
        "net_value_musd": g["net_value_usd"].sum() / 1e6,
    })


plan_totals = plan_df.groupby("country")[["hires_requested", "terminations_requested"]].sum()
summary = pd.DataFrame({
    "agents_jan": country_parameters_df.set_index("country")["agents_jan_2026"],
    "agents_dec": results_df[results_df["month"] == "2026-12"].set_index("country")["agents_active"],
    "hired": plan_totals["hires_requested"],
    "terminated": plan_totals["terminations_requested"],
}).join(yearly(results_df)).join(yearly(keep_staff)[["net_value_musd"]].rename(
    columns={"net_value_musd": "keep_staff_net_musd"}))
summary.sort_values("net_value_musd", ascending=False).round(1)
```

---

**[code cell]**

```python
totals = pd.DataFrame({
    "recommended plan": results_df[["incremental_revenue_usd", "salary_cost_usd",
                                    "termination_cost_usd", "net_value_usd"]].sum(),
    "keep starting staff": keep_staff[["incremental_revenue_usd", "salary_cost_usd",
                                       "termination_cost_usd", "net_value_usd"]].sum(),
}) / 1e6
totals.index = ["revenue uplift ($M)", "salaries ($M)", "termination costs ($M)", "net value ($M)"]
totals.round(1)
```

---

**[code cell]**

```python
# Month-by-month decisions: + hires, - terminations (notice given that month)
changes = plan_df.assign(change=plan_df["hires_requested"] - plan_df["terminations_requested"])
changes.pivot(index="country", columns="month", values="change")
```

---

**[markdown cell]**

**Reading the plan**
- `agents_jan` vs `agents_dec` shows how far each country's headcount moves. Large January
  terminations mean the starting staff is well above what demand needs. Paying 40% of salary
  once is cheaper than paying idle agents all year.
- `expired` should be near zero wherever serving is profitable. Countries where it isn't are the
  ones where an agent costs more than the uplift they create.
- `avg_wait_days` is the price of running lean. Waiting costs no revenue in this model as long as
  the advertiser is picked up within 60 days, so the plan uses the waiting line as a buffer.
- Hires land one month before demand rises, because new agents need a month of training.

---

**[markdown cell]**

## 5. Sensitivity analysis *(Mer McFadden)*

The forecast won't be exact, so we check how the **recommended plan, unchanged**, performs if
sign-ups come in 20% lower or higher than forecast in every country. The plan stays fixed and
only demand changes. (To re-plan for a different demand level instead, the GenAI assistant in
section 6 calls `run_scenario`, which re-optimizes.)

---

**[code cell]**

```python
from src.optimization.scenarios import sensitivity_table

sens = sensitivity_table((0.8, 1.0, 1.2)).set_index("demand_multiplier")
money = ["incremental_revenue_usd", "total_cost_usd", "net_value_usd"]
sens[money] = sens[money] / 1e6
sens.round(1)
```

---

**[markdown cell]**

**Revenue basis (D4).** Our headline counts each supported advertiser's uplift as 13.5% of their
*annual* budget. If the uplift only applied to the 60 days of support (60/365 of that), each
agent is worth about a sixth as much. We re-optimize under that assumption to see how much the
plan depends on it.

---

**[code cell]**

```python
from src.optimization.optimizer import optimize_staffing

window_plan, window_results = optimize_staffing(
    demand_df, country_parameters_df, uplift_basis="support_window")  # about 40 s
dec = lambda r: r[r["month"] == "2026-12"].set_index("country")["agents_active"]
basis = pd.DataFrame({
    "agents_dec_annual": dec(results_df),
    "agents_dec_60_day": dec(window_results),
    "expired_annual": results_df.groupby("country")["advertisers_expired"].sum(),
    "expired_60_day": window_results.groupby("country")["advertisers_expired"].sum(),
})
basis.round(0)
```

---

**[markdown cell]**

**Reading the sensitivity results**
- At **−20%**, costs don't change (same plan), so net value falls by the full drop in revenue.
- At **+20%**, watch `advertisers_expired` and `advertisers_waiting_dec_31`. The plan runs close
  to capacity, so extra sign-ups mostly wait or expire and revenue barely rises. Re-optimizing
  (section 6) shows what extra hiring would be worth.
- Under the **60-day revenue basis**, countries with low budgets relative to salaries are cut back,
  and some of their sign-ups expire. Where both bases keep similar headcounts, the plan doesn't
  depend on the D4 choice. Small differences in either direction can also come from the search
  stopping at slightly different plans (see the limitations in section 7).

---

**[code cell]**

```python
from src.optimization.scenarios import write_outputs

write_outputs()  # outputs/plan_2026.csv (264 rows) and outputs/staffing_plan_2026.csv
```

---
---

# Text for other parts of the submission

## For the README (component description)

> **Staffing optimization and scenarios (Mer McFadden).** `src/optimization/optimizer.py` chooses monthly hires and terminations for each of the 22 countries to maximize 2026 net value: revenue uplift minus salaries and termination costs. It starts from either the current headcount or a demand-based plan, then improves it with a local search that scores each candidate plan with the simulator. `src/optimization/scenarios.py` provides the recommended plan, the ±20% sensitivity table, and `run_scenario`, which re-plans under different demand and is what the GenAI assistant calls. `python -m src.optimization.optimizer` writes `outputs/plan_2026.csv`. See `src/optimization/README.md` for how to call it, and `tests/test_optimization.py` for test cases.

## For notebook section 7 (limitations and other considerations)

> **Optimizer limitations**
> - **Heuristic search.** The local search finds a good plan, not a proven best one. It can stop at a plan where no single move helps but a combination of moves would. On the sample data, a search three times slower found plans worth only 0.25% more in total.
> - **2026 only (D8).** Costs and revenue after December 31 are ignored, so the plan under-prepares for January 2027: hiring late in the year looks like pure cost. An optional year-end floor (`year_end_floor=True`) keeps enough agents for advertisers still in support on January 1, 2027. It's off by default because, in countries where agents don't pay for themselves, it forces hires that lose money.
> - **Waiting is free in the model.** Revenue doesn't depend on how long an advertiser waits, as long as it is under 60 days, so the plan runs lean and lets advertisers wait. In practice long waits likely hurt satisfaction and uplift. A cost per waiting day would push the plan toward more staff.
> - **Serving every advertiser isn't a goal.** Where agents cost more than the uplift they create, the plan lets sign-ups expire. Google may value serving them for other reasons (retention, market growth) that aren't in the numbers.
> - **One forecast.** The plan is optimized for the expected forecast. The sensitivity table shows how it holds up at ±20%, but the plan isn't built to hedge against that uncertainty.
> - **Big one-time cuts.** Where starting staff far exceeds demand, the plan makes large January terminations. Real constraints (labor rules, morale, hiring capacity) would likely spread these out.

## For notebook section 8 (contributions and AI use)

> **Mer McFadden:** also built and tested the staffing optimizer, sensitivity analysis and scenario interface (`src/optimization/`); wrote notebook sections 4 and 5.

> **AI use (Role 3).** Claude Code (an AI coding assistant) wrote the optimizer tests and then the optimizer and scenario code in `src/optimization/`, and drafted the integration guide and this section's text, analysis cells and video script. Mer made the modeling decisions (objective, re-optimizing in `run_scenario` while keeping the plan fixed in the sensitivity table, and leaving the year-end floor off by default). The code was checked with hand-calculable tests and an independent AI code review. Details are in `docs/AI_USE.md`.

## For the video (about 30 seconds)

> **[Show: section 4 summary table, sorted by net value]**
> "The optimizer picks monthly hires and terminations for all 22 countries to maximize 2026 net value. It tries thousands of plans per country, and the simulator scores each one."
>
> **[Show: the `agents_jan` and `agents_dec` columns, then the month-by-month decisions table]**
> "Most countries start with far more agents than demand needs, so the plan makes cuts in January and hires again ahead of busy months, allowing for the month of training."
>
> **[Show: the section 5 sensitivity table]**
> "We also tested the plan with sign-ups 20% lower and higher than forecast, and the assistant can re-plan for any scenario on request."
