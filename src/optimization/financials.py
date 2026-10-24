"""Member 3 — Cost and revenue calculations.

Keep the formulas here so the simulator, optimizer, and notebook all use the same ones.
"""

EXPECTED_UPLIFT = 0.135  # mean of the uplift distribution supplied in the challenge
SUPPORT_DAYS = 60

# See docs/assumptions.md, decision D4. "annual" is the headline assumption;
# "support_window" is kept for the sensitivity analysis.
UPLIFT_BASES = ("annual", "support_window")


def incremental_revenue(
    n_supported: float,
    mean_annual_budget_usd: float,
    uplift_basis: str = "annual",
) -> float:
    """Revenue uplift attributed to supporting `n_supported` advertisers."""
    if uplift_basis == "annual":
        share_of_year = 1.0
    elif uplift_basis == "support_window":
        share_of_year = SUPPORT_DAYS / 365
    else:
        raise ValueError(f"uplift_basis must be one of {UPLIFT_BASES}, got {uplift_basis!r}")
    return n_supported * mean_annual_budget_usd * EXPECTED_UPLIFT * share_of_year


def termination_cost(n_terminated: int, annual_salary_usd: float) -> float:
    return n_terminated * 0.40 * annual_salary_usd
