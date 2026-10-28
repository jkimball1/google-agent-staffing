# Modeling assumptions

These decisions affect more than one module, so we settle them **before** independent work starts. Each one has a provisional choice so nobody is blocked. If you disagree, comment on the decision (or open an Issue) by **Saturday**. After that, changes need a PR that updates this file.

Status: 🟡 provisional · 🟢 agreed · 🔴 disputed

## Given by the challenge (not up for debate)

- 22 countries, monthly plan for January–December 2026
- Starting headcount = January 2026 levels from the workbook
- Each agent supports at most **10** advertisers at a time
- Each advertiser is supported for **60 days**
- Advertisers can wait up to **60 days** for assignment
- New agents need **one month** of training
- Terminating an agent costs **40% of annual salary** and requires **one month's notice**
- **Eligible** means `Projected_Annual_Budget` is strictly greater than (**>**) the country's `Advertiser_Eligibility_Threshold_USD`. Ineligible advertisers get no support.
- All agents start 2026 with **no advertisers assigned**
- An agent can take a new advertiser at any time while holding fewer than 10. Each advertiser graduates individually 60 days after pickup.
- Each advertiser's budget is fixed for the whole year
- Headcount can change at any point in a month. Ramp-up and notice periods still apply.
- The workbook has **920 records dated 2025-02-29**, an invalid date that needs an explicit cleaning decision. Pandas and Excel read these as text, not dates.
- Uplift distribution (expected value **13.5%**):

  | Uplift | 0% | 5% | 10% | 15% | 20% | 25% |
  |---|---|---|---|---|---|---|
  | Probability | 5% | 15% | 25% | 25% | 20% | 10% |

## Decisions

| # | Decision | Provisional choice | Owner | Status |
|---|---|---|---|---|
| D1 | **Invalid 2025-02-29 dates** | Keep the 920 records and spread them evenly over the 28 days of Feb 2025. Dropping them would understate February demand, and moving them all to Feb 28 would create a one-day spike. Report the alternatives and their effect on the forecast. **Effect:** spreading, moving to Feb 28 or to Mar 1 give the same 2026 total (≈103,800 eligible); dropping lowers it by 0.75% (≈780), nearly all in February. `clean_signups(feb29_rule=...)` implements all four. | Member 1 | 🟡 |
| D2 | **Forecast method** | Per-country 2026 total = 2025 eligible sign-ups × 2024→2025 growth, with each country's growth shrunk toward the all-country growth by its sampling noise (on this data every country gets the shared −1.5%, since country differences are within noise). Monthly shape = one seasonal profile pooled across countries and averaged over 2024–2025 (country-specific profiles didn't repeat year to year and backtested worse). Each month's total is spread evenly across its days. Annual budget = 2024–2025 mean of each country's eligible advertisers (no trend or seasonality). Implemented in `src/forecasting/forecast.py`; see notebook section 2. | Member 1 | 🟡 |
| D3 | **Timing** | Staffing decisions are made on the 1st of each month. Hires are paid from that month and become productive on the 1st of the next month. Terminations: notice is given on the 1st and the 40% cost is charged that month. The agent is paid through the notice month, takes no new advertisers during it, and leaves on the 1st of the next month. Within a day, events happen in this order: graduations, then agents arriving or leaving (on the 1st), then expiries, then new arrivals join the back of the line, then the line is served first come, first served. So a sign-up can be served the day it arrives. | Member 2 | 🟢 |
| D4 | **Revenue from support** | **Headline:** uplift = 13.5% × `Projected_Annual_Budget` per supported advertiser. The budget is annual and fixed for the year, and the 60 days is how long an advertiser occupies an agent, not how long the uplift lasts. **Sensitivity:** `uplift_basis="support_window"` (× 60/365) is kept as a setting in `financials.py`, and the notebook reports whether the plan changes under it. | Member 3 | 🟢 |
| D5 | **Termination with active advertisers** | Each country's agents are one shared pool. While agents are on notice, new advertisers are only assigned if the agents who are staying could hold everyone (free slots = 10 × staying agents − all occupied slots), so the pool keeps room to absorb the departing agents' advertisers. When agents leave, remaining agents take over their advertisers if they have free slots. Advertisers who can't be taken over lose the rest of their support, and the uplift for the days they miss is removed in the month the agent leaves (e.g. 1 of 60 days missed removes 1/60 of their uplift). December notices leave on Jan 1, 2027, and the same rule applies then, with any loss booked in December. Only productive agents can be terminated (not trainees); terminating more than that raises an error. | Member 2 | 🟢 |
| D6 | **Waiting line** | First come, first served within each country, with no sharing of agents across countries. An advertiser can be assigned on day 60 of waiting at the latest and is removed after that. Advertiser counts can be fractional, because forecasts are expected values. Agent counts are whole numbers. | Member 2 | 🟢 |
| D8 | **Objective** | Maximize total 2026 net value (revenue − salary − termination costs) across all countries. Countries are planned separately (D6) with a documented local-search heuristic (`src/optimization/README.md`). **Year end:** nothing after Dec 31, 2026 is counted, so the plan tends to under-prepare for January 2027. An optional floor (`year_end_floor=True`) keeps enough agents on Jan 1, 2027 to hold advertisers still in support; it's off by default because, where agents cost more than they earn, it forces hires that lose money. **Waiting:** uplift doesn't depend on wait time (under 60 days), so the plan may let advertisers wait; average wait is reported. **Scenarios:** `run_scenario` re-optimizes for the scaled demand; the ±20% sensitivity table keeps the recommended plan fixed. | Member 3 | 🟢 |

D7 (eligibility) was removed because the challenge defines it; see the rules above. Numbers were kept so existing references stay valid.

## Open questions

Add questions here as they come up: write the question, give a provisional answer, and @ the people affected.

-
