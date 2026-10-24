# Data findings

First look at `DADS5250_Hackathon_Google_Data.xlsx`. Reproduce with `data/sample/make_samples.py` plus pandas.
"Need" = agents required to serve every eligible advertiser immediately: eligible sign-ups in the trailing 60 days ÷ 10, computed day by day. **Avg** is the 2025 average. **Peak** is the highest single day in 2024 or 2025. This assumes 2026 demand looks like 2024–25 and ignores the 60-day waiting allowance, which would lower the peak somewhat.

## Headlines

1. **The company is overstaffed overall, but less than a simple average suggests.** There are 6,474 agents today. Serving every eligible advertiser needs about 1,685 on average, but about **2,540 at the peak**. The fair comparison is roughly **2.5×**, not 3.8×. Even if *every* sign-up were supported regardless of eligibility, the peak would need about 5,440 agents, still fewer than today's headcount.
   - **Understaffed:** **Vietnam** (59 agents vs ~118 at peak, about half of what's needed).
   - **About right at peak:** **South Africa** (78 vs ~75) and **India** (428 vs ~341). Cuts there are small or limited to off-peak months.
   - **Heavily overstaffed:** Germany, France, Thailand (~5×), Argentina (~9×), UAE (~12×).
2. **So in most countries the main decision is when and how fast to cut staff.** Vietnam needs hiring, and South Africa and India need little change. Firing costs 40% of annual salary (about 4.8 months of pay) plus a month of notice. An agent who would sit idle for more than about 5 months is cheaper to let go.
3. **Demand has a strong Q4 peak.** Eligible sign-ups in Oct–Dec run about 1.3–1.6× the rest of the year, in both 2024 and 2025. Whatever we cut to, we need enough agents for the peak, or we need to rehire before it (hires need a month of training).
4. **Year-over-year demand is flat to slightly down** (about −1.5% overall). Day of the week makes no visible difference.
5. **About 42.5% of sign-ups are eligible.** 13 rows sit exactly at the threshold and are not eligible under the strict ">" rule.
6. **The 920 rows dated 2025-02-29** are spread across all 22 countries. See D1.

## Economics per agent (full utilization, 2025 mean eligible budget)

An agent at full capacity serves about 61 advertisers a year (10 slots × 365 ÷ 60 days).

| Country | Agents now | Avg need | Peak need | Salary | Revenue / agent (annual basis) | Revenue / agent (60-day basis) |
|---|---|---|---|---|---|---|
| Vietnam | 59 | 77 | 118 | 17,904 | 142,654 | 23,421 |
| South Africa | 78 | 47 | 75 | 26,078 | 84,437 | 13,870 |
| India | 428 | 230 | 341 | 14,118 | 382,094 | 62,841 |
| Brazil | 189 | 91 | 132 | 27,950 | 517,388 | 85,045 |
| Spain | 150 | 58 | 86 | 33,814 | 179,032 | 29,443 |
| China | 252 | 93 | 139 | 22,265 | 593,855 | 97,638 |
| Japan | 297 | 106 | 160 | 49,545 | 359,342 | 59,069 |
| Poland | 150 | 48 | 67 | 38,769 | 137,422 | 22,569 |
| Canada | 228 | 73 | 114 | 61,060 | 380,512 | 62,537 |
| Turkey | 102 | 33 | 52 | 24,566 | 105,059 | 17,277 |
| USA | 652 | 208 | 312 | 77,721 | 710,047 | 116,739 |
| South Korea | 199 | 60 | 91 | 38,354 | 229,707 | 37,778 |
| Indonesia | 120 | 29 | 44 | 15,728 | 183,534 | 30,173 |
| Italy | 350 | 82 | 125 | 43,087 | 247,652 | 40,698 |
| Mexico | 442 | 77 | 123 | 19,789 | 194,241 | 31,938 |
| UK | 589 | 98 | 145 | 51,650 | 509,053 | 83,707 |
| Australia | 450 | 73 | 116 | 43,505 | 318,219 | 52,317 |
| Germany | 602 | 86 | 128 | 51,328 | 472,858 | 77,745 |
| Thailand | 139 | 20 | 27 | 24,289 | 79,996 | 13,140 |
| France | 489 | 66 | 95 | 65,384 | 406,488 | 66,795 |
| Argentina | 200 | 14 | 22 | 18,687 | 92,284 | 15,148 |
| UAE | 309 | 16 | 26 | 65,115 | 28,774 | 4,745 |

**What this means for D4 (the revenue rule):**
- **On the annual basis**, a fully used agent earns far more than their salary everywhere except **UAE**, where the average eligible budget is only about $3,500. So the plan should serve every eligible advertiser, except possibly in UAE.
- **On the 60-day basis**, staffing loses money in about half the countries, including Spain, Poland, Italy, Turkey, Thailand, South Africa, Argentina and UAE. The "optimal" plan would be to stop supporting advertisers there entirely, which is not a plausible reading of the case. That supports the annual basis as the headline.
- The eligibility thresholds are **not** set at break-even (UAE's threshold is $1,000), so the check proposed earlier in D4 doesn't apply.
