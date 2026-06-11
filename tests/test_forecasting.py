import pytest
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.forecasting.predict import forecast


def test_forecast_returns_correct_horizon():
    result = forecast("CA_1", "FOODS_3_001", horizon=7)
    assert len(result["dates"]) == 7
    assert len(result["forecast"]) == 7


def test_forecast_positive_values():
    result = forecast("CA_1", "FOODS_3_001", horizon=14)
    assert all(v >= 0 for v in result["forecast"])


def test_forecast_total_units_matches_sum():
    result = forecast("CA_1", "FOODS_3_001", horizon=7)
    assert abs(result["total_forecast_units"] - sum(result["forecast"])) < 0.5


def test_forecast_invalid_store_returns_error():
    result = forecast("INVALID_STORE", "FOODS_3_001", horizon=7)
    assert "error" in result


def test_forecast_invalid_item_returns_error():
    result = forecast("CA_1", "INVALID_ITEM_999", horizon=7)
    assert "error" in result


def test_forecast_dates_are_sequential():
    result = forecast("CA_1", "FOODS_3_001", horizon=7)
    dates = pd.to_datetime(result["dates"])
    deltas = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
    assert all(d == 1 for d in deltas)
