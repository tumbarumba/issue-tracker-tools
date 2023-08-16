from __future__ import annotations

from datetime import datetime, timedelta
from math import ceil
from typing import List

import numpy
import pandas
from dateutil.parser import isoparse


class FlowData:
    TREND_PERIOD: int = 14
    MINIMUM_TREND_SLOPE = 0.001

    def __init__(self: FlowData, data_frame: pandas.DataFrame, today: datetime.date):
        self.today = today
        self.dates = self._load_dates(data_frame, today)
        self.pending = data_frame["pending"].tolist()[: len(self.dates)]
        self.in_progress = data_frame["in_progress"].tolist()[: len(self.dates)]
        self.done = data_frame["done"].tolist()[: len(self.dates)]
        self.total = data_frame["total"].tolist()[: len(self.dates)]
        self.slope_history = self._calculate_slopes()
        self.current_trend = self._calculate_current_trend()
        self.optimistic_trend = self._calculate_optimistic_trend()
        self.pessimistic_trend = self._calculate_pessimistic_trend()

    def _load_dates(self, data_frame, last_date):
        all_dates = list(
            map(lambda date_str: isoparse(date_str).date(), data_frame["date"])
        )
        last_index = all_dates.index(last_date)
        return all_dates[: last_index + 1]

    def _calculate_slopes(self) -> List[float]:
        result = []
        for index in range(len(self.done)):
            regression_values = self._select_regression_values(index)
            if len(regression_values) > 1:
                trend = calculate_trend_coefficients(regression_values)
                result.append(trend.slope)
            else:
                result.append(numpy.float64(1.0))
        return result

    def _select_regression_values(self, last_index):
        start = max(0, last_index - FlowData.TREND_PERIOD)
        return self.done[start : last_index + 1]  # noqa

    def _calculate_current_trend(self):
        current_slope = self.slope_history[-1]
        return Trend(current_slope, self._calculate_implied_y_intercept(current_slope))

    def _calculate_optimistic_trend(self):
        optimistic_slope = max(self.slope_history[-FlowData.TREND_PERIOD :])  # noqa
        return Trend(
            optimistic_slope, self._calculate_implied_y_intercept(optimistic_slope)
        )

    def _calculate_pessimistic_trend(self):
        pessimistic_slope = min(self.slope_history[-FlowData.TREND_PERIOD :])  # noqa
        return Trend(
            pessimistic_slope, self._calculate_implied_y_intercept(pessimistic_slope)
        )

    def _calculate_implied_y_intercept(self: FlowData, slope: float):
        """Force the calculated value of today's done to match the actual value by adjusting the intercept"""
        index_today = (self.today - self.dates[0]).days
        done_today = self.done[index_today]
        return done_today - (index_today * slope)

    def _predicted_end_index(self: FlowData, trend: Trend) -> int | None:
        if trend.slope < FlowData.MINIMUM_TREND_SLOPE:
            return None

        final_scope = self.total[-1]
        return ceil((final_scope - trend.intercept) / trend.slope)

    def _predicted_end_date(self: FlowData, trend: Trend) -> datetime.date:
        end_index = self._predicted_end_index(trend)
        if not end_index:
            return None

        start_date = self.dates[0]
        return start_date + timedelta(days=self._predicted_end_index(trend))

    @property
    def optimistic_completion_date(self: FlowData) -> datetime.date:
        return self._predicted_end_date(self.optimistic_trend)

    @property
    def pessimistic_completion_date(self: FlowData) -> datetime.date:
        return self._predicted_end_date(self.pessimistic_trend)


class Trend:
    """Regression coefficients for a linear trend line"""

    def __init__(self: Trend, slope: float, intercept: float):
        self.slope = slope
        self.intercept = intercept

    def __str__(self: Trend) -> str:
        return f"Trend({self.slope:n},{self.intercept:n})"


def calculate_trend_coefficients(trend_values) -> Trend:
    coefficients = numpy.polyfit(range(len(trend_values)), trend_values, 1)[:2]
    return Trend(coefficients[0], coefficients[1])
