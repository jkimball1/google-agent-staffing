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
!python -m pytest -q tests/test_simulation.py
```
