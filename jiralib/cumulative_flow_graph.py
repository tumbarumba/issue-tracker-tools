from __future__ import annotations
from typing import List
from matplotlib.lines import Line2D
import matplotlib.pyplot as pyplot
import matplotlib.patches as patches
import pandas
import os
import sys
import numpy
from datetime import datetime, timedelta
from dateutil.parser import isoparse
from math import ceil

from .config import ProjectConfig

colour_schemes = {
    "sunset": {
        "Done": "#e76f51",
        "In Progress": "#f4a261",
        "Pending": "#e9c46a",
        "Current Date": "#A188A6",
        "Predicted End Date": "#788AA3",
        "Milestone": "indigo",
        "Trendline": "midnightblue"
    },
    "electric": {
        "Done": "#87F5FB",
        "In Progress": "#DE3C4B",
        "Pending": "#240115",
        "Current Date": "#4C956C",
        "Predicted End Date": "#788AA3",
        "Milestone": "indigo",
        "Trendline": "midnightblue"
    },
    "pastels": {
        "Done": "#0FA3B1",
        "In Progress": "#B5E2FA",
        "Pending": "#F7A072",
        "Current Date": "#9FB798",
        "Predicted End Date": "#EDB6A3",
        "Milestone": "#764248",
        "Trendline": "#5F634F"
    },
    "default": {
        "Done": "#CCEBC5",
        "In Progress": "#B3CDE3",
        "Pending": "#CCCCCC",
        "Current Date": "#9FB798",
        "Predicted End Date": "#EDB6A3",
        "Milestone": "#764248",
        "Trendline": "#5F634F"
    }
}


class FlowData:
    TREND_PERIOD: int = 14
    MINIMUM_TREND_SLOPE = 0.001

    def __init__(self: FlowData, data_frame: pandas.DataFrame, today: datetime.date):
        self.today = today
        self.dates = self._load_dates(data_frame, today)
        self.pending = data_frame["pending"].tolist()[:len(self.dates)]
        self.in_progress = data_frame["in_progress"].tolist()[:len(self.dates)]
        self.done = data_frame["done"].tolist()[:len(self.dates)]
        self.total = data_frame["total"].tolist()[:len(self.dates)]
        self.slope_history = self._calculate_slopes()
        self.current_trend = self._calculate_current_trend()
        self.optimistic_trend = self._calculate_optimistic_trend()
        self.pessimistic_trend = self._calculate_pessimistic_trend()

    def _load_dates(self, data_frame, last_date):
        all_dates = list(map(lambda date_str: isoparse(date_str).date(), data_frame["date"]))
        last_index = all_dates.index(last_date)
        return all_dates[:last_index+1]

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
        return self.done[start:last_index + 1]

    def _calculate_current_trend(self):
        current_slope = self.slope_history[-1]
        return Trend(current_slope, self._calculate_implied_y_intercept(current_slope))

    def _calculate_optimistic_trend(self):
        optimistic_slope = max(self.slope_history[-FlowData.TREND_PERIOD:])
        return Trend(optimistic_slope, self._calculate_implied_y_intercept(optimistic_slope))

    def _calculate_pessimistic_trend(self):
        pessimistic_slope = min(self.slope_history[-FlowData.TREND_PERIOD:])
        return Trend(pessimistic_slope, self._calculate_implied_y_intercept(pessimistic_slope))

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


class CumulativeFlowGraph:
    def __init__(self: CumulativeFlowGraph, project_config: ProjectConfig, csv_file: str, png_file: str,
                 today: datetime.date):
        self.project_config = project_config
        self.csv_file = csv_file
        self.png_file = png_file
        self.today = today

    def run(self, open_graph):
        print(f"Reading cumulative flow data from {str(self.csv_file)}")
        flow_data = self.read_csv_values()
        self.build_graph(flow_data)

        if open_graph:
            os.system(f"xdg-open '{self.png_file}'")

    def build_graph(self, flow_data):
        colours = colour_schemes["default"]
        legend_elements = self.generate_legend(colours, flow_data)

        final_x_axis, final_y_axis = self.select_final_axis(flow_data)

        max_scope = max(flow_data.total)
        max_y_scale = ceil(max_scope * 1.1)

        self.write_stacked_area_graph(final_x_axis, final_y_axis, max_y_scale, legend_elements, colours)
        self.write_current_trend_line(final_x_axis, flow_data, colours)
        self.write_optimistic_trend_line(final_x_axis, flow_data, colours)
        self.write_pessimistic_trend_line(final_x_axis, flow_data, colours)
        end_date = flow_data.pessimistic_completion_date
        if end_date:
            self.write_milestone_dates(max(flow_data.total), final_x_axis, end_date, colours)
        self.set_plot_size()

        pyplot.gcf().canvas.draw()

        self.save_graph()

    def read_csv_values(self):
        data_frame = pandas.read_csv(self.csv_file)
        return FlowData(data_frame, self.today)

    def select_final_axis(self, flow_data):
        start_date = flow_data.dates[0]
        end_date = self.calc_end_date(flow_data)

        final_x_axis = pandas.date_range(start_date, end_date).date.tolist()

        required_size = len(final_x_axis)
        final_y_axis = [
            self.normalise_series(flow_data.done, required_size),
            self.normalise_series(flow_data.in_progress, required_size),
            self.normalise_series(flow_data.pending, required_size),
        ]
        return final_x_axis, final_y_axis

    @property
    def final_milestone_date(self):
        final_milestone = self.project_config.milestones[-1]
        return final_milestone["date"]

    def calc_end_date(self, flow_data):
        milestone_date = self.final_milestone_date
        predicted_end_date = self.last_milestone_or_end_date(flow_data, milestone_date)
        if (predicted_end_date - milestone_date).days < 15:
            # if final milestone and predicted finish are relatively close show both
            end_date = max(predicted_end_date, milestone_date) + timedelta(days=2)
        else:
            end_date = milestone_date + timedelta(days=15)
        return end_date

    def last_milestone_or_end_date(self, flow_data, milestone_date):
        return (
                flow_data.pessimistic_completion_date
                or flow_data.optimistic_completion_date
                or milestone_date
        )

    def normalise_series(self, series_values, required_size):
        result = series_values[:]
        while len(result) < required_size:
            result.append(series_values[-1])

        return result

    def generate_legend(self, colours, flow_data):
        """generates a list of all the information need to show the legend"""
        # Manual list of stackplot legend elements.
        legend_elements = [
            patches.Patch(facecolor=colours["Pending"], label="Pending"),
            patches.Patch(facecolor=colours["In Progress"], label="In Progress"),
            patches.Patch(facecolor=colours["Done"], label="Done"),
            Line2D([0], [0], color=colours["Current Date"], label=f"{self.today} (Today)"),
        ]
        if flow_data.optimistic_completion_date:
            legend_elements.append(Line2D([0], [0], color=colours["Predicted End Date"],
                                          label=f"{flow_data.optimistic_completion_date} (Optimistic End)"))
        if flow_data.pessimistic_completion_date:
            legend_elements.append(Line2D([0], [0], color=colours["Predicted End Date"],
                                          label=f"{flow_data.pessimistic_completion_date} (Pessimistic End)"))
        for milestone in self.project_config.milestones:
            legend_elements.append(Line2D([0], [0],
                                   color=colours["Milestone"],
                                   label=f"{milestone['date']} ({milestone['name']})"))

        return legend_elements

    def write_stacked_area_graph(self, final_x_axis, final_y_axis, max_y_scale, legend_elements, colours):
        """All formatting graph visuals"""
        pyplot.stackplot(final_x_axis, final_y_axis, colors=[colours["Done"], colours["In Progress"], colours["Pending"]])
        pyplot.legend(handles=legend_elements, loc='upper left')
        pyplot.xticks(rotation=90)
        pyplot.xlabel("Dates", labelpad=12, fontsize=12)
        pyplot.ylabel("Total Stories", labelpad=9, fontsize=12)
        pyplot.ylim([0, max_y_scale])
        pyplot.title(self.project_config.project_name, pad=9, fontsize=16)
        pyplot.gca().margins(0, 0)

    def write_current_trend_line(self, final_x_axis, flow_data, colours):
        """Plots linear regression line"""
        start_date = self.today + timedelta(days=-FlowData.TREND_PERIOD+1)
        if start_date < final_x_axis[0]:
            start_date = final_x_axis[0]
        end_date = self.today
        self.write_trend_line(final_x_axis, colours, start_date, end_date, flow_data.current_trend)

    def write_optimistic_trend_line(self, final_x_axis, flow_data, colours):
        """Plots linear regression line"""
        start_date = self.today
        end_date = final_x_axis[-1]
        self.write_trend_line(final_x_axis, colours, start_date, end_date, flow_data.optimistic_trend)

    def write_pessimistic_trend_line(self, final_x_axis, flow_data, colours):
        """Plots linear regression line"""
        start_date = self.today
        end_date = final_x_axis[-1]
        self.write_trend_line(final_x_axis, colours, start_date, end_date, flow_data.pessimistic_trend)

    def write_trend_line(self, final_x_axis, colours, start_date, end_date, trend):
        """Plots linear regression line"""
        trend_dates = pandas.date_range(start_date, end_date).date.tolist()

        start_index = final_x_axis.index(start_date)
        end_index = final_x_axis.index(end_date)

        x_values = range(start_index, end_index + 1)
        y_values = trend.slope * x_values + trend.intercept
        pyplot.plot(trend_dates, y_values, color=colours["Trendline"])

    def write_milestone_dates(self, max_total, final_x_axis, predicted_end_date, colours):
        """checks for existence of data + calls writing func"""
        self.write_date_line(max_total, self.today, colours["Current Date"])
        if self.project_config.milestones is not None:
            for i in range(len(self.project_config.milestones)):
                milestone = self.project_config.milestones[i]
                if milestone["date"] in final_x_axis:
                    self.write_date_line(max_total, milestone["date"], colours["Milestone"])
                else:
                    sys.exit(f'Error: Milestone "{milestone["date"]}" has no date.')

        if predicted_end_date in final_x_axis:
            self.write_date_line(max_total, predicted_end_date, colours["Predicted End Date"])

    def write_date_line(self, max_total, x_axis_position_index, line_color):
        """plots date lines"""
        pyplot.vlines(x_axis_position_index, 0, max_total+(max_total/6), color=line_color)

    def set_plot_size(self):
        figure = pyplot.gcf()

        figure.subplots_adjust(left=0.05, right=0.95, bottom=.1, top=0.95)

        new_width = 1920.0 / figure.dpi
        new_height = new_width / 16 * 9
        figure.set_size_inches(new_width, new_height)

    def save_graph(self):
        """saves graph, creates file locations if necessary"""
        pyplot.savefig(self.png_file)
        print(f"Cumulative flow graph saved as {self.png_file}")
