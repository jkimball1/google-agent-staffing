"""Member 3 — Cost and revenue calculations.

Keep the formulas here so the simulator, optimizer, and notebook all use the same ones.
"""

EXPECTED_UPLIFT = 0.135  # mean of the uplift distribution supplied in the challenge


def incremental_revenue(n_supported: float, mean_annual_budget_usd: float) -> float:
    """Revenue uplift attributed to supporting `n_supported` advertisers.

    How the uplift is applied (annual budget vs. 60-day window) is an open
    decision — see docs/assumptions.md, decision D4.
    """
    raise NotImplementedError


def termination_cost(n_terminated: int, annual_salary_usd: float) -> float:
    return n_terminated * 0.40 * annual_salary_usd
