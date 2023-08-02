import math
import pandas as pd
import numpy as np
from datetime import date, timedelta

from lib.cfd.cumulative_flow_graph import FlowData, Trend


def test_uniform_trend() -> None:
    today = date(2023, 6, 30)
    df = uniform_progress_df(today)

    flow_data = FlowData(df, today)

    assert flow_data.pending == df["pending"].tolist()
    assert math.isclose(flow_data.slope_history[0], 1.0)
    assert math.isclose(flow_data.slope_history[1], 1.0)
    assert math.isclose(flow_data.slope_history[-1], 1.0)
    assert_equal_trends(flow_data.current_trend, Trend(1.0, 0.0))
    assert_equal_trends(flow_data.optimistic_trend, Trend(1.0, 0.0))
    assert_equal_trends(flow_data.pessimistic_trend, Trend(1.0, 0.0))


def test_increasing_trend() -> None:
    today = date(2023, 6, 30)
    df = increasing_progress_df(today)

    flow_data = FlowData(df, today)

    assert math.isclose(flow_data.slope_history[0], 1.0)
    assert math.isclose(flow_data.slope_history[1], 1.0)
    assert math.isclose(flow_data.slope_history[-1], 4.14286, abs_tol=1e-04)
    assert_equal_trends(flow_data.current_trend, Trend(4.14286, -7.14286))
    assert_equal_trends(flow_data.optimistic_trend, Trend(4.14286, -7.14286))
    assert_equal_trends(flow_data.pessimistic_trend, Trend(1.0, 40.0))


def test_dates_after_today_are_excluded() -> None:
    today = date(2023, 6, 28)
    final_date = date(2023, 6, 30)
    df = increasing_progress_df(final_date)

    flow_data = FlowData(df, today)

    assert flow_data.dates[-1] == today
    assert flow_data.pending[-1] == 50
    assert flow_data.in_progress[-1] == 5
    assert flow_data.done[-1] == 45
    assert flow_data.total[-1] == 100


def uniform_progress_df(final_date) -> pd.DataFrame:
    dates = date_array(final_date, 16)
    return pd.DataFrame({
        "date":         dates,
        "pending":      [19, 18, 17, 16, 15, 14, 13, 12, 11, 10,  9,  8,  7,  6,  5,  4],  # noqa
        "in_progress":  [ 1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1],  # noqa
        "done":         [ 0,  1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12, 13, 14, 15],  # noqa
        "total":        [20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20],  # noqa
    })


def increasing_progress_df(final_date) -> pd.DataFrame:
    dates = date_array(final_date, 16)
    return pd.DataFrame({
        "date":         dates,
        "pending":      [ 99,  98,  97,  96,  95,  90,  85,  80,  75,  70,  65,  60,  55,  50,  45,  40],  # noqa
        "in_progress":  [  1,   1,   1,   1,   1,   5,   5,   5,   5,   5,   5,   5,   5,   5,   5,   5],  # noqa
        "done":         [  0,   1,   2,   3,   4,   5,  10,  15,  20,  25,  30,  35,  40,  45,  50,  55],  # noqa
        "total":        [100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100],  # noqa
    })


def date_array(final_date, size):
    """sequential dates ending in final_date"""
    return np.array([str(final_date + timedelta(days=i)) for i in range(1 - size, 1)])


def assert_equal_trends(actual: Trend, expected: Trend) -> None:
    assert math.isclose(actual.slope, expected.slope, abs_tol=1e-04)\
       and math.isclose(actual.intercept, expected.intercept, abs_tol=1e-04),\
       f"{actual} should be {expected}"
