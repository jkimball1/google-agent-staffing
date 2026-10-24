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
- An agent can take a new advertiser at any time while holding ≤ 10. Each advertiser graduates individually 60 days after pickup.
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
| D1 | **Invalid 2025-02-29 dates** | Keep the 920 records and spread them evenly over the 28 days of Feb 2025. Dropping them would understate February demand. Moving them all to Feb 28 would make that day about 2.8× a normal day (1,989 vs ~709 sign-ups), a spike that doesn't exist. Report the alternatives and their effect on the forecast. | Member 1 | 🟡 |
| D2 | **Forecast method** | Per-country monthly trend from 2024–2025, with seasonality if the data supports it, spread evenly across days. Annual budget = recent mean of eligible advertisers per country. | Member 1 | 🟡 |
| D3 | **Training and notice timing** | The challenge allows changes at any point in the month; we simplify to monthly decisions. Decisions are made at the start of month *m*. Hires are paid from *m* and productive from *m+1*. Terminated agents are paid through *m* (notice), stop taking new assignments in *m*, and leave at the start of *m+1*. | Member 2 | 🟡 |
| D4 | **Revenue from support** | **Headline:** uplift = 13.5% × `Projected_Annual_Budget` per supported advertiser. The budget is annual and fixed for the year, and the 60 days is how long an advertiser occupies an agent, not how long the uplift lasts. **Sensitivity:** `uplift_basis="support_window"` (× 60/365) is kept as a setting in `financials.py`, and the notebook reports whether the plan changes under it. Data check: on the 60-day basis, staffing loses money in about half the countries, which supports the annual basis (see `docs/data_findings.md`). | Member 3 | 🟢 |
| D5 | **Agents with active assignments at termination** | Their current advertisers stay through the notice month. If an assignment would extend past departure, it is reassigned to free capacity or counted as lost support. Simplest valid option: only terminate agents whose slots are free. | Member 2 | 🟡 |
| D6 | **Queue order** | First-come, first-served within each country. No sharing of agents between countries. | Member 2 | 🟡 |
| D8 | **Objective** | Maximize total 2026 net value (revenue − salary − termination costs) across all countries. | Member 3 | 🟡 |

## Open questions

Add questions here as they come up: write the question, give a provisional answer, and @ the people affected.

-
