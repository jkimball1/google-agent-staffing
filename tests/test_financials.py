import pytest

from src.optimization.financials import incremental_revenue, termination_cost


def test_annual_basis_is_default():
    assert incremental_revenue(10, 20_000) == pytest.approx(10 * 20_000 * 0.135)


def test_support_window_basis_scales_by_60_days():
    assert incremental_revenue(10, 20_000, "support_window") == pytest.approx(
        10 * 20_000 * 0.135 * 60 / 365)


def test_unknown_basis_raises():
    with pytest.raises(ValueError):
        incremental_revenue(1, 1, "monthly")


def test_termination_cost_is_40_percent_of_salary():
    assert termination_cost(2, 50_000) == pytest.approx(40_000)
