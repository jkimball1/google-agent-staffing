# Data findings

First look at `DADS5250_Hackathon_Google_Data.xlsx`. Reproduce with `data/sample/make_samples.py` plus pandas.
"Needed" is a rough steady-state estimate: eligible arrivals per day × 60 days ÷ 10 per agent, using 2025 volume. It ignores seasonality and waiting.

## Headlines

1. **The company is heavily overstaffed.** There are 6,474 agents today against roughly 1,732 needed on average. Only **Vietnam** is understaffed (59 agents vs ~79 needed). Most countries have 2–7× what they need, and UAE has about 19×.
2. **So the main decision is when and how fast to cut staff**, not how many to hire. Firing costs 40% of annual salary (about 4.8 months of pay) plus a month of notice. An agent who would sit idle for more than about 5 months is cheaper to let go.
3. **Demand has a strong Q4 peak.** Eligible sign-ups in Oct–Dec run about 1.3–1.6× the rest of the year, in both 2024 and 2025. Whatever we cut to, we need enough agents for the peak, or we need to rehire before it (hires need a month of training).
4. **Year-over-year demand is flat to slightly down** (about −1.5% overall). Day of the week makes no visible difference.
5. **About 42.5% of sign-ups are eligible.** 13 rows sit exactly at the threshold and are not eligible under the strict ">" rule.
6. **The 920 rows dated 2025-02-29** are spread across all 22 countries. See D1.

## Economics per agent (full utilization, 2025 mean eligible budget)

An agent at full capacity serves about 61 advertisers a year (10 slots × 365 ÷ 60 days).

| Country | Agents now | Needed | Salary | Revenue / agent (annual basis) | Revenue / agent (60-day basis) |
|---|---|---|---|---|---|
| Vietnam | 59 | 79 | 17,904 | 142,654 | 23,421 |
| South Africa | 78 | 48 | 26,078 | 84,437 | 13,870 |
| India | 428 | 237 | 14,118 | 382,094 | 62,841 |
| Brazil | 189 | 93 | 27,950 | 517,388 | 85,045 |
| Spain | 150 | 60 | 33,814 | 179,032 | 29,443 |
| China | 252 | 95 | 22,265 | 593,855 | 97,638 |
| Japan | 297 | 110 | 49,545 | 359,342 | 59,069 |
| Poland | 150 | 50 | 38,769 | 137,422 | 22,569 |
| Canada | 228 | 76 | 61,060 | 380,512 | 62,537 |
| Turkey | 102 | 34 | 24,566 | 105,059 | 17,277 |
| USA | 652 | 213 | 77,721 | 710,047 | 116,739 |
| South Korea | 199 | 61 | 38,354 | 229,707 | 37,778 |
| Indonesia | 120 | 30 | 15,728 | 183,534 | 30,173 |
| Italy | 350 | 84 | 43,087 | 247,652 | 40,698 |
| Mexico | 442 | 79 | 19,789 | 194,241 | 31,938 |
| UK | 589 | 101 | 51,650 | 509,053 | 83,707 |
| Australia | 450 | 75 | 43,505 | 318,219 | 52,317 |
| Germany | 602 | 88 | 51,328 | 472,858 | 77,745 |
| Thailand | 139 | 20 | 24,289 | 79,996 | 13,140 |
| France | 489 | 68 | 65,384 | 406,488 | 66,795 |
| Argentina | 200 | 15 | 18,687 | 92,284 | 15,148 |
| UAE | 309 | 16 | 65,115 | 28,774 | 4,745 |

**What this means for D4 (the revenue rule):**
- **On the annual basis**, a fully used agent earns far more than their salary everywhere except **UAE**, where the average eligible budget is only about $3,500. So the plan should serve every eligible advertiser, except possibly in UAE.
- **On the 60-day basis**, staffing loses money in about half the countries, including Spain, Poland, Italy, Turkey, Thailand, South Africa, Argentina and UAE. The "optimal" plan would be to stop supporting advertisers there entirely, which is not a plausible reading of the case. That supports the annual basis as the headline.
- The eligibility thresholds are **not** set at break-even (UAE's threshold is $1,000), so the check proposed earlier in D4 doesn't apply.
