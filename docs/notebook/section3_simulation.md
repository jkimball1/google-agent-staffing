# Notebook section 3: Staffing simulation (draft for integration)

Author: Mer McFadden (Role 2). For whoever assembles `notebooks/final_submission.ipynb` to paste in.
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
  over lose the rest of their support, and the uplift for the days they miss is removed. While
  someone is on notice, new advertisers are only taken on if the staying agents could hold
  everyone, so the pool keeps room for the departing agent's advertisers.
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
- **February:** one agent is given notice (cost: 40% × $12,000 = $4,800). They still count in
  `agents_active` (2) because they work through the notice month, but take no new advertisers,
  so the 5 keep waiting.
- **March 1:** the agent leaves while all 20 advertisers still have a day of support left. The
  remaining agent can hold only 10, so **10 lose support**. They miss 1 of their 60 days, so 1/60
  of their uplift is removed: 10 × $1,350 ÷ 60 = $225.
- **March 2:** the remaining 10 graduate, freeing the slots. The 5 waiting advertisers are
  assigned on **day 60** of waiting, the last day they're allowed to be. Their uplift
  (5 × $1,350 = $6,750) less the $225 removed gives March's $6,525.

Giving notice a month later (leaving April 1, after these advertisers graduate on March 2)
would have lost nothing. Timing cuts around when advertisers graduate is the kind of trade-off
the optimizer weighs in section 4.

---

**[markdown cell]**

### Checking the simulator

The rules above are covered by small automated tests whose answers can be worked out by hand.
Full 22-country runs check the agreed output format and that every eligible sign-up ends up
supported, expired or still waiting. Malformed inputs (mismatched country names, wrong dates,
duplicate rows, fractional hires) must raise a clear error instead of producing a misleading plan.

---

**[code cell]**

```python
import pytest
pytest.main(["-q", str(ROOT / "tests" / "test_simulation.py")])
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
> - **End-of-year horizon.** Only 2026 costs and revenue are counted, which pushes in two directions. A termination late in the year pays the full 40% cost but saves only a month or two of 2026 salary, so Q4 cuts look unattractive even if those agents would sit idle into 2027. On the other side, advertisers assigned in November and December are credited their full uplift while the agent time that supports them into 2027 is free. December's headcount isn't checked against what early 2027 will need, and advertisers still waiting on December 31 are left unresolved.
> - **Prorated loss when support is cut short.** If a termination strands advertisers, they lose uplift in proportion to the support days they miss. In reality a partial loss of support may not reduce uplift exactly proportionally.
> - **No cross-country help.** Agents can't cover other countries, even where language would allow it.
> - **Identical agents.** Every agent has the same capacity from their first productive day. No attrition, ramp-up curve or absences.

## For notebook section 8 (contributions)

> **Mer McFadden:** set up the repository, shared interfaces and modeling assumptions; built and tested the staffing simulator (`src/simulation/`); wrote notebook section 3.

## For the video (about 25 seconds)

> "Every number in our plan comes from a day-by-day simulator. New advertisers get an agent if one has a free slot, or wait up to 60 days. The rules: 10 advertisers per agent, 60 days of support, one month to train or terminate. In this example, an agent leaves one day before their advertisers graduate, cutting 10 advertisers' support short. The optimizer and the assistant both run plans through it."

*(Suggested visual: the worked-example table from section 3.)*
