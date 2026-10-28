# Notebook section 2: Historical data and demand forecast (draft for integration)

Author: Jasper Kimball (Role 1). For whoever assembles `notebooks/final_submission.ipynb` to paste in.
Each block below is marked **[markdown cell]** or **[code cell]**. The code cells assume the
notebook's setup cell has already put the repo root on `sys.path` and defined `ROOT`. They don't
need any variables from other sections, and they define `demand_df` and `country_parameters_df`
for later sections. Text for the README, sections 7 and 8, and the video is at the end. See
`docs/notebook/README.md` for the format.

---

**[markdown cell]**

## 2. Historical data and demand forecast *(Jasper Kimball)*

The workbook holds **499,644 advertiser sign-ups** from 2024–2025 across 22 countries. The
staffing model only cares about **eligible** advertisers: those whose projected annual budget is
strictly greater than their country's threshold. `src/forecasting/forecast.py` cleans the
sign-ups, counts eligible ones by country and month, and forecasts daily eligible arrivals for
every day of 2026. That forecast (`demand_df`) is the input to the simulator, the optimizer and
the planning assistant.

**Cleaning (D1).** The data has no missing values or duplicate IDs. The one problem is
**920 sign-ups dated 2025-02-29**, a date that doesn't exist (2025 isn't a leap year). We keep
them and spread them evenly over February 1–28, 2025. Dropping them would understate February
demand, and the table below shows that the other options barely change the forecast.

---

**[code cell]**

```python
import pandas as pd
from src.forecasting import forecast as fc

WORKBOOK = str(ROOT / "data" / "raw" / "DADS5250_Hackathon_Google_Data.xlsx")

country_parameters_df = fc.load_country_parameters(WORKBOOK)
raw = fc.load_workbook(WORKBOOK)[fc.SIGNUPS_SHEET]
signups = fc.clean_signups(raw)
eligible = fc.eligible_signups(signups, country_parameters_df)

print(f"Sign-ups: {len(raw):,}  ·  dated 2025-02-29: {(raw['Sign_Up_Date'] == '2025-02-29').sum()}")
print(f"Eligible (budget > country threshold): {len(eligible):,} ({len(eligible) / len(raw):.1%})")
eligible.groupby(eligible["Sign_Up_Date"].dt.year).size().rename("eligible sign-ups").to_frame()
```

---

**[code cell]**

```python
# How the 2025-02-29 rule changes the 2026 forecast
rules = {}
for rule in fc.FEB29_RULES:
    by_month = fc.forecast_monthly(WORKBOOK, rule).groupby("month")["eligible_signups"].sum()
    rules[rule] = {"2026 total": by_month.sum(), "Feb 2026": by_month["2026-02"],
                   "Mar 2026": by_month["2026-03"]}
pd.DataFrame(rules).T.round(0)
```

---

**[markdown cell]**

Spreading the records, moving them to Feb 28, and moving them to Mar 1 all give the same annual
total (about 103,800). Dropping them lowers it by about 0.75% (≈780 advertisers), almost all of
it in February. Spreading and moving to Feb 28 give identical forecasts, because the forecast
works with monthly totals; spreading just avoids a fake one-day spike in the history.

### Forecast method (D2)

1. **Seasonality.** Eligible sign-ups jump about 35% above average in **October–December** in
   both years. We use one monthly profile for all countries, averaged over 2024 and 2025.
   We also tried a separate profile per country, but those country-specific patterns didn't repeat
   from one year to the next (correlation ≈ 0), and predicting 2025 from 2024 was less accurate
   with them (monthly error 14.5% vs 13.5% for the shared profile).
2. **Trend.** Eligible sign-ups fell **1.5%** from 2024 to 2025 across all countries. Each
   country's own change ranges from −5.7% (Mexico) to +4.0% (Thailand), but those differences are
   no bigger than random variation would produce for countries of this size. So we shrink each
   country's growth toward the shared trend by how noisy it is. On this data, every country ends
   up using the shared −1.5%.
3. **2026 forecast** = each country's 2025 eligible sign-ups × (1 − 1.5%) × the monthly profile,
   with each month's total spread evenly over its days.
4. **Budget.** Average budgets of eligible advertisers didn't change between years or across
   months, so each country uses its 2024–2025 average for all of 2026.

---

**[code cell]**

```python
history = fc.monthly_history(eligible)
trend = fc.annual_forecast(history)
trend[["country", "signups_2024", "signups_2025", "growth_observed", "growth_used",
       "signups_2026"]].round(3).sort_values("signups_2026", ascending=False)
```

---

**[code cell]**

```python
import matplotlib.pyplot as plt

monthly_forecast = fc.forecast_monthly(WORKBOOK)
past = history.sum(axis=0)
past.index = pd.PeriodIndex(past.index, freq="M").to_timestamp()
future = monthly_forecast.groupby("month")["eligible_signups"].sum()
future.index = pd.PeriodIndex(future.index, freq="M").to_timestamp()

fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(past.index, past.values, marker="o", label="Actual eligible sign-ups (2024–2025)")
ax.plot(future.index, future.values, marker="o", linestyle="--", label="Forecast (2026)")
ax.set_ylabel("Eligible sign-ups per month (all countries)")
ax.set_title("Eligible advertiser sign-ups: history and 2026 forecast")
ax.legend()
plt.tight_layout()
plt.show()
```

---

**[markdown cell]**

### The forecast handed to the rest of the model

`demand_df` has one row per country per day of 2026 (22 × 365 = 8,030 rows), in the format
agreed in `INTERFACES.md`. `country_parameters_df` holds each country's salary, eligibility
threshold and January 2026 headcount, read directly from the workbook.

---

**[code cell]**

```python
from src.schemas import DEMAND_COLUMNS, validate

demand_df = validate(fc.forecast_demand(WORKBOOK), DEMAND_COLUMNS, "demand_df")
print(f"{len(demand_df):,} rows · {demand_df['country'].nunique()} countries · "
      f"{demand_df['eligible_signups'].sum():,.0f} eligible advertisers forecast for 2026")
demand_df.head()
```

---

**[code cell]**

```python
import pytest
pytest.main(["-q", str(ROOT / "tests" / "test_forecasting.py")])
```

---
---

# Text for other parts of the submission

## For the README (component description)

> **Data and forecasting (Jasper Kimball).** `src/forecasting/forecast.py` reads the course workbook, fixes the 920 invalid 2025-02-29 dates by spreading them over February, and keeps only eligible advertisers (budget strictly above the country threshold). It forecasts daily eligible sign-ups for every country in 2026 as 2025's level × the shared 2024→2025 trend (−1.5%) × a monthly seasonal profile with an October–December peak. It also returns each country's average advertiser budget and the country parameters (salary, threshold, starting headcount). Its output, `demand_df`, feeds the simulator, the optimizer and the planning assistant. Tests are in `tests/test_forecasting.py`.

## For notebook section 7 (limitations and other considerations)

> **Forecast limitations**
> - **Two years of history.** The trend is one year-over-year step, so it can't tell a lasting decline from a one-off dip. The seasonal profile is an average of only two years, and those years differ noticeably (for example, June 2025 was much weaker than June 2024).
> - **Shared seasonality and trend.** Every country gets the same monthly shape and the same −1.5% trend, because the country-level differences in this data are within random variation. A real local event (a holiday calendar, a market launch) wouldn't show up.
> - **No day-of-week or holiday pattern.** Each month's demand is spread evenly over its days. Day-of-week differences in the data are small (within about ±6%), and the 60-day support and waiting windows smooth them out.
> - **A single expected value.** The forecast is a point estimate, with no range. Uncertainty is handled by the ±20% scenarios in section 5.
> - **Eligibility shares and budgets held at historical levels.** About 42.5% of sign-ups were eligible in both years and average budgets were flat, so we assume the same in 2026.

## For notebook section 8 (contributions and AI use)

> **Jasper Kimball:** built and tested the data cleaning and demand forecast (`src/forecasting/`); wrote notebook section 2; assembled the README and recorded the video.

> **AI use (Role 1).** Claude Code (an AI coding assistant) explored the sign-up data, wrote the forecasting module in `src/forecasting/forecast.py` and its tests, and drafted this section's text, plot and video script. Claude Code proposed the method from that exploration, and Jasper reviewed it. The work was checked by tests with hand-calculable answers, by comparing the shared and per-country seasonal profiles on 2024→2025 data, by comparing the four 2025-02-29 cleaning rules, and by running the full pipeline and test suite on the real forecast. Details are in `docs/AI_USE.md`.

## For the video (about 30 seconds)

> **[Show: section 2 heading and the cleaning output (sign-up counts and the 920 invalid dates)]**
> "We start with half a million advertiser sign-ups. About 42% have budgets above their country's threshold and qualify for support. 920 records had an impossible date, February 29, 2025, so we spread them across February instead of dropping them."
>
> **[Show: the history-and-forecast plot, pointing at the October–December peaks]**
> "Demand peaks every October through December, and fell about 1.5% from 2024 to 2025. Our 2026 forecast keeps that seasonal shape and trend, for about 104,000 eligible advertisers."
>
> **[Show: `demand_df.head()`]**
> "The result is a daily forecast for each of the 22 countries, which drives every staffing decision that follows."
