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
| D1 | **Invalid 2025-02-29 dates** | Keep the 920 records and spread them evenly over the 28 days of Feb 2025. Dropping them would understate February demand, and moving them all to Feb 28 would create a one-day spike. Report the alternatives and their effect on the forecast. | Member 1 | 🟡 |
| D2 | **Forecast method** | Per-country monthly trend from 2024–2025, with seasonality if the data supports it, spread evenly across days. Annual budget = recent mean of eligible advertisers per country. | Member 1 | 🟡 |
| D3 | **Timing** | Staffing decisions are made on the 1st of each month. Hires are paid from that month and become productive on the 1st of the next month. Terminations: notice is given on the 1st and the 40% cost is charged that month. The agent is paid through the notice month, takes no new advertisers during it, and leaves on the 1st of the next month. Within a day, events happen in this order: graduations, then agents arriving or leaving (on the 1st), then expiries, then the waiting line is served, then new arrivals. | Member 2 | 🟢 |
| D4 | **Revenue from support** | **Headline:** uplift = 13.5% × `Projected_Annual_Budget` per supported advertiser. The budget is annual and fixed for the year, and the 60 days is how long an advertiser occupies an agent, not how long the uplift lasts. **Sensitivity:** `uplift_basis="support_window"` (× 60/365) is kept as a setting in `financials.py`, and the notebook reports whether the plan changes under it. | Member 3 | 🟢 |
| D5 | **Termination with active advertisers** | Each country's agents are one shared pool. When agents leave, remaining agents take over their advertisers if they have free slots. Advertisers who can't be taken over lose the rest of their support, and their revenue is removed in the month the agent leaves. Terminating more agents than are currently employed raises an error. | Member 2 | 🟢 |
| D6 | **Waiting line** | First come, first served within each country, with no sharing of agents across countries. An advertiser can be assigned on day 60 of waiting at the latest and is removed after that. Advertiser counts can be fractional, because forecasts are expected values. Agent counts are whole numbers. | Member 2 | 🟢 |
| D8 | **Objective** | Maximize total 2026 net value (revenue − salary − termination costs) across all countries. | Member 3 | 🟡 |

## Open questions

Add questions here as they come up: write the question, give a provisional answer, and @ the people affected.

-
