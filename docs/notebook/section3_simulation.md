# Notebook section 3: Staffing simulation (draft for integration)

Author: Mer McFadden (Role 2). For Enrique to paste into `notebooks/final_submission.ipynb`.
Each block below is marked **[markdown cell]** or **[code cell]**. The code cells assume the
notebook's setup cell has already put the repo root on `sys.path`.

---

**[markdown cell]**

## 3. Staffing simulation *(Mer McFadden)*

Every staffing number in this notebook comes from one simulator, `src/simulation/simulator.py`.
Given daily demand and a monthly hiring/termination plan, it plays out 2026 **day by day** for
each country, then summarizes each month. The optimizer (section 4), the sensitivity analysis
(section 5) and the planning assistant (section 6) all call it to evaluate plans.

**Rules from the challenge**
- Each productive agent supports at most **10** advertisers at a time.
- Each advertiser is supported for **60 days**, then graduates and frees the slot.
- Eligible advertisers who can't be assigned wait up to **60 days**, then are removed with no uplift.
- New hires spend **one month** in training before they can take advertisers.
- Terminations need **one month's notice** and cost **40%** of annual salary.
- All agents start 2026 with no advertisers assigned.

**Our modeling decisions** (details in `docs/assumptions.md`)
- **Timing (D3):** staffing decisions take effect on the 1st of each month. Trainees are paid
  during training. Agents serving notice are paid, keep their current advertisers, but take no new ones.
- **Terminations (D5):** each country's agents are one shared pool. When agents leave, the
  remaining agents take over their advertisers if they have free slots. Any who can't be taken
  over lose the rest of their support, and their revenue is removed. This makes badly timed
  cuts costly, so the optimizer avoids them.
- **Waiting line (D6):** first come, first served within each country. An advertiser can be
  assigned on day 60 of waiting at the latest.
- **Revenue (D4):** an advertiser's uplift (expected 13.5% of annual budget) is booked when
  their support starts.

---

**[markdown cell]**

### A worked example

One country with **2 agents** gets **25 sign-ups on January 1**, and one agent is given notice
in February. Every advertiser has a $10,000 budget, and agents earn $12,000 a year.

---

**[code cell]**

```python
import numpy as np
from src.simulation.simulator import simulate_country

arrivals = np.zeros(365)
arrivals[0] = 25  # 25 sign-ups on Jan 1

example = simulate_country(
    daily_arrivals=arrivals,
    daily_budget=np.full(365, 10_000),
    agents_start=2,
    hires=[0] * 12,
    terminations=[0, 1] + [0] * 10,  # one termination in February
    annual_salary=12_000,
)
example.loc["2026-01":"2026-04", [
    "agents_active", "agents_terminated", "advertisers_supported",
    "advertisers_waiting", "advertisers_support_lost", "average_wait_days",
    "incremental_revenue_usd", "total_cost_usd",
]]
```

---

**[markdown cell]**

What happens:
- **January:** 2 agents can hold 20 advertisers, so 20 start support and **5 wait**.
- **February:** one agent is given notice (cost: 40% × $12,000 = $4,800). They keep their
  advertisers but take no new ones, so the 5 keep waiting.
- **March 1:** the agent leaves while all 20 advertisers still have a day of support left. The
  remaining agent can hold only 10, so **10 lose support** and their uplift is removed.
- **March 2:** the remaining 10 graduate, freeing the slots. The 5 waiting advertisers are
  assigned on **day 60** of waiting, the last day they're allowed to be.

That one termination, made a month too early, wiped out the uplift for 10 advertisers. This is
the trade-off the optimizer weighs in section 4.

---

**[markdown cell]**

### Checking the simulator

The rules above are covered by small automated tests whose answers can be worked out by hand,
plus a check that a full 22-country run produces output in the agreed format.

---

**[code cell]**

```python
!cd "{ROOT}" && python -m pytest -q tests/test_simulation.py
```

---
---

# Text for other parts of the submission

## For the README (component description)

> **Staffing simulation (Mer McFadden).** `src/simulation/simulator.py` plays out a staffing plan day by day for each country, then summarizes it by month. It applies the challenge's rules: 10 advertisers per agent, 60-day support, a 60-day waiting limit, one month of training, and one month's notice with a 40% termination cost. For each country and month it reports headcount, advertisers supported, waiting and expired, utilization, revenue uplift, and costs. The optimizer, the sensitivity analysis and the planning assistant all use it to evaluate staffing plans. See `src/simulation/README.md` for how to call it, and `tests/test_simulation.py` for hand-checkable test cases.

## For notebook section 7 (limitations and other considerations)

> **Simulator limitations**
> - **Monthly decisions.** The challenge allows hiring and firing at any point in a month. We only make changes on the 1st, which is simpler but may leave some savings on the table.
> - **Agents as a shared pool.** Within each country we track total capacity, not individual agent–advertiser pairs. Real reassignment when an agent leaves would be messier than "anyone with a free slot takes over."
> - **Demand is treated as known.** Each run uses one demand forecast. Uncertainty is handled by re-running at ±20% (section 5), not by modeling day-to-day randomness.
> - **Expected uplift, not the distribution.** Each supported advertiser is worth the expected 13.5% uplift. Individual outcomes range from 0% to 25%.
> - **End-of-year horizon.** Revenue is booked when support starts, so December assignments count fully even though support continues into 2027, while 2027 salaries aren't counted. Advertisers still waiting on December 31 are left unresolved. Staffing decisions late in the year should be read with this in mind.
> - **No cross-country help.** Agents can't cover other countries, even where language would allow it.
> - **Identical agents.** Every agent has the same capacity from their first productive day. No attrition, ramp-up curve or absences.

## For notebook section 8 (contributions)

> **Mer McFadden:** set up the repository, shared interfaces and modeling assumptions; built and tested the staffing simulator (`src/simulation/`); wrote notebook section 3.

## For the video (about 25 seconds)

> "Under every number in our plan is a day-by-day simulator. Each day, new eligible advertisers arrive, get an agent if one has a free slot, or wait for up to 60 days. Agents hold 10 advertisers for 60 days each, new hires train for a month, and terminations take a month's notice and cost 40% of salary. Here's a small example: one termination timed a month too early cuts off support for 10 advertisers and wipes out their uplift. The optimizer uses this simulator to test staffing plans, and the assistant calls it to answer what-if questions."

*(Suggested visual: the worked-example table from section 3.)*
