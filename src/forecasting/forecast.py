"""Member 1 — Data preparation and demand forecasting.

Owner: TBD
Branch: feature/forecasting
"""

import pandas as pd

from src.schemas import COUNTRY_PARAMETERS_COLUMNS, DEMAND_COLUMNS


def load_workbook(workbook_path: str) -> dict[str, pd.DataFrame]:
    """Read every sheet of the course workbook into DataFrames, keyed by sheet name."""
    raise NotImplementedError


def clean_signups(signups: pd.DataFrame) -> pd.DataFrame:
    """Clean raw 2024–2025 sign-ups.

    Must handle the 920 records dated 2025-02-29 (not a real date).
    Record the chosen rule and its justification in docs/assumptions.md.
    """
    raise NotImplementedError


def load_country_parameters(workbook_path: str) -> pd.DataFrame:
    """Return one row per country with COUNTRY_PARAMETERS_COLUMNS."""
    raise NotImplementedError


def forecast_demand(workbook_path: str) -> pd.DataFrame:
    """Forecast daily eligible sign-ups for every country for all of 2026.

    Returns a DataFrame with DEMAND_COLUMNS (see INTERFACES.md).
    Until this is implemented, other modules use data/sample/sample_demand.csv.
    """
    raise NotImplementedError
