from __future__ import annotations

from datetime import datetime, timedelta
from dateutil.parser import isoparse
from math import ceil
from typing import List

import numpy
import pandas


class FlowData:
    DEFAULT_TREND_PERIOD: int = 14
    MINIMUM_TREND_SLOPE = 0.001
    DEFAULT_SLOPE = numpy.float64(1.0)

    def __init__(self, data_frame: pandas.DataFrame,
                 today: datetime.date,
                 trend_period: int | None = None,
                 initial_slope: float | None = None):
        self.today = today
        self.dates = self._load_dates(data_frame, today)
        self.pending = data_frame["pending"].tolist()[: len(self.dates)]
        self.in_progress = data_frame["in_progress"].tolist()[: len(self.dates)]
        self.done = data_frame["done"].tolist()[: len(self.dates)]
        self.total = data_frame["total"].tolist()[: len(self.dates)]
        self.trend_period = trend_period or FlowData.DEFAULT_TREND_PERIOD
        self.initial_slope = numpy.float64(initial_slope) if initial_slope else FlowData.DEFAULT_SLOPE
        self.slope_history = self._calculate_all_slopes()
        self.current_trend = self._calculate_current_trend()
        self.optimistic_trend = self._calculate_optimistic_trend()
        self.pessimistic_trend = self._calculate_pessimistic_trend()

    def _load_dates(self, data_frame, last_date):
        all_dates = [isoparse(date_str).date() for date_str in data_frame["date"]]
        last_index = all_dates.index(last_date)
        return all_dates[: last_index + 1]

    def _calculate_all_slopes(self) -> List[float]:
        """Calculate regression slopes for recent entries in the 'done' column"""
        last_index = len(self.done)
        first_index = max(0, last_index - self.trend_period)
        return [self._calculate_slope(index) for index in range(first_index, last_index)]

    def _calculate_slope(self, last_index: int) -> float:
        """Calculate the regression slope at the give index of the 'done' column"""
        first_index = max(0, last_index - self.trend_period)
        regression_values = self.done[first_index : last_index + 1]  # noqa

        if len(regression_values) < 2:
            return self.initial_slope

        trend = calculate_trend_coefficients(regression_values)
        return trend.slope

    def _calculate_current_trend(self):
        current_slope = self.slope_history[-1]
        return Trend(current_slope, self._calculate_implied_y_intercept(current_slope))

    def _calculate_optimistic_trend(self):
        optimistic_slope = max(self.slope_history)
        return Trend(optimistic_slope, self._calculate_implied_y_intercept(optimistic_slope))

    def _calculate_pessimistic_trend(self):
        pessimistic_slope = min(self.slope_history)
        return Trend(pessimistic_slope, self._calculate_implied_y_intercept(pessimistic_slope))

    def _calculate_implied_y_intercept(self, slope: float):
        """Force the calculated value of today's done to match the actual value by adjusting the intercept"""
        index_today = (self.today - self.dates[0]).days
        done_today = self.done[index_today]
        return done_today - (index_today * slope)

    def _predicted_end_index(self, trend: Trend) -> int | None:
        if trend.slope < FlowData.MINIMUM_TREND_SLOPE:
            return None

        final_scope = self.total[-1]
        return ceil((final_scope - trend.intercept) / trend.slope)

    def _predicted_end_date(self, trend: Trend) -> datetime.date:
        end_index = self._predicted_end_index(trend)
        if not end_index:
            return None

        start_date = self.dates[0]
        return start_date + timedelta(days=self._predicted_end_index(trend))

    @property
    def optimistic_completion_date(self) -> datetime.date:
        return self._predicted_end_date(self.optimistic_trend)

    @property
    def pessimistic_completion_date(self) -> datetime.date:
        return self._predicted_end_date(self.pessimistic_trend)


class Trend:
    """Regression coefficients for a linear trend line"""

    def __init__(self, slope: float, intercept: float):
        self.slope = slope
        self.intercept = intercept

    def __str__(self) -> str:
        return f"Trend({self.slope:n},{self.intercept:n})"


def calculate_trend_coefficients(trend_values) -> Trend:
    coefficients = numpy.polyfit(range(len(trend_values)), trend_values, 1)[:2]
    return Trend(coefficients[0], coefficients[1])
