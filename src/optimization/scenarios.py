"""Member 3 — Sensitivity analysis and the scenario entry point used by the GenAI app.

run_scenario() is the main hook between the planning model and the assistant:
the assistant calls it to compute new numbers instead of describing a static table.
"""

import pandas as pd


def run_scenario(demand_multiplier: float = 1.0, country: str | None = None) -> pd.DataFrame:
    """Re-run the pipeline with demand scaled by `demand_multiplier`.

    If `country` is given, only that country's demand is scaled.
    Returns RESULTS_COLUMNS for all countries and months.
    """
    raise NotImplementedError


def sensitivity_table(multipliers=(0.8, 1.0, 1.2)) -> pd.DataFrame:
    """Compare the recommended plan under each demand multiplier (the +/-20% analysis)."""
    raise NotImplementedError
