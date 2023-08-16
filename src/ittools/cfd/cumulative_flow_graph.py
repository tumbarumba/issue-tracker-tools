from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from math import ceil

import matplotlib.patches as patches
import matplotlib.pyplot as pyplot
import pandas
from matplotlib.lines import Line2D

from ittools.config import ProjectConfig
from .flow_data import FlowData

colour_schemes = {
    "sunset": {
        "Done": "#e76f51",
        "In Progress": "#f4a261",
        "Pending": "#e9c46a",
        "Current Date": "#A188A6",
        "Predicted End Date": "#788AA3",
        "Milestone": "indigo",
        "Trendline": "midnightblue",
    },
    "electric": {
        "Done": "#87F5FB",
        "In Progress": "#DE3C4B",
        "Pending": "#240115",
        "Current Date": "#4C956C",
        "Predicted End Date": "#788AA3",
        "Milestone": "indigo",
        "Trendline": "midnightblue",
    },
    "pastels": {
        "Done": "#0FA3B1",
        "In Progress": "#B5E2FA",
        "Pending": "#F7A072",
        "Current Date": "#9FB798",
        "Predicted End Date": "#EDB6A3",
        "Milestone": "#764248",
        "Trendline": "#5F634F",
    },
    "default": {
        "Done": "#CCEBC5",
        "In Progress": "#B3CDE3",
        "Pending": "#CCCCCC",
        "Current Date": "#9FB798",
        "Predicted End Date": "#EDB6A3",
        "Milestone": "#764248",
        "Trendline": "#5F634F",
    },
}


class CumulativeFlowGraph:
    def __init__(
        self: CumulativeFlowGraph,
        project_config: ProjectConfig,
        csv_file: str,
        png_file: str,
        report_date: datetime.date,
    ):
        self.project_config = project_config
        self.csv_file = csv_file
        self.png_file = png_file
        self.report_date = report_date

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

        self.write_stacked_area_graph(
            final_x_axis, final_y_axis, max_y_scale, legend_elements, colours
        )
        self.write_current_trend_line(final_x_axis, flow_data, colours)
        self.write_optimistic_trend_line(final_x_axis, flow_data, colours)
        self.write_pessimistic_trend_line(final_x_axis, flow_data, colours)
        end_date = flow_data.pessimistic_completion_date
        if end_date:
            self.write_milestone_dates(
                max(flow_data.total), final_x_axis, end_date, colours
            )
        self.set_plot_size()

        pyplot.gcf().canvas.draw()

        self.save_graph()

    def read_csv_values(self):
        data_frame = pandas.read_csv(self.csv_file)
        return FlowData(data_frame, self.report_date)

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
            Line2D(
                [0],
                [0],
                color=colours["Current Date"],
                label=f"{self.report_date} (Today)",
            ),
        ]
        if flow_data.optimistic_completion_date:
            legend_elements.append(
                Line2D(
                    [0],
                    [0],
                    color=colours["Predicted End Date"],
                    label=f"{flow_data.optimistic_completion_date} (Optimistic End)",
                )
            )
        if flow_data.pessimistic_completion_date:
            legend_elements.append(
                Line2D(
                    [0],
                    [0],
                    color=colours["Predicted End Date"],
                    label=f"{flow_data.pessimistic_completion_date} (Pessimistic End)",
                )
            )
        for milestone in self.project_config.milestones:
            legend_elements.append(
                Line2D(
                    [0],
                    [0],
                    color=colours["Milestone"],
                    label=f"{milestone['date']} ({milestone['name']})",
                )
            )

        return legend_elements

    def write_stacked_area_graph(
        self, final_x_axis, final_y_axis, max_y_scale, legend_elements, colours
    ):
        """All formatting graph visuals"""
        pyplot.stackplot(
            final_x_axis,
            final_y_axis,
            colors=[colours["Done"], colours["In Progress"], colours["Pending"]],
        )
        pyplot.legend(handles=legend_elements, loc="upper left")
        pyplot.xticks(rotation=90)
        pyplot.xlabel("Dates", labelpad=12, fontsize=12)
        pyplot.ylabel("Total Stories", labelpad=9, fontsize=12)
        pyplot.ylim([0, max_y_scale])
        pyplot.title(self.project_config.name, pad=9, fontsize=16)
        pyplot.gca().margins(0, 0)

    def write_current_trend_line(self, final_x_axis, flow_data, colours):
        """Plots linear regression line"""
        start_date = self.report_date + timedelta(days=-FlowData.TREND_PERIOD + 1)
        if start_date < final_x_axis[0]:
            start_date = final_x_axis[0]
        end_date = self.report_date
        self.write_trend_line(
            final_x_axis, colours, start_date, end_date, flow_data.current_trend
        )

    def write_optimistic_trend_line(self, final_x_axis, flow_data, colours):
        """Plots linear regression line"""
        start_date = self.report_date
        end_date = final_x_axis[-1]
        self.write_trend_line(
            final_x_axis, colours, start_date, end_date, flow_data.optimistic_trend
        )

    def write_pessimistic_trend_line(self, final_x_axis, flow_data, colours):
        """Plots linear regression line"""
        start_date = self.report_date
        end_date = final_x_axis[-1]
        self.write_trend_line(
            final_x_axis, colours, start_date, end_date, flow_data.pessimistic_trend
        )

    def write_trend_line(self, final_x_axis, colours, start_date, end_date, trend):
        """Plots linear regression line"""
        trend_dates = pandas.date_range(start_date, end_date).date.tolist()

        start_index = final_x_axis.index(start_date)
        end_index = final_x_axis.index(end_date)

        x_values = range(start_index, end_index + 1)
        y_values = trend.slope * x_values + trend.intercept
        pyplot.plot(trend_dates, y_values, color=colours["Trendline"])

    def write_milestone_dates(
        self, max_total, final_x_axis, predicted_end_date, colours
    ):
        """checks for existence of data + calls writing func"""
        self.write_date_line(max_total, self.report_date, colours["Current Date"])
        if self.project_config.milestones is not None:
            for i in range(len(self.project_config.milestones)):
                milestone = self.project_config.milestones[i]
                if milestone["date"] in final_x_axis:
                    self.write_date_line(
                        max_total, milestone["date"], colours["Milestone"]
                    )
                else:
                    sys.exit(f'Error: Milestone "{milestone["date"]}" has no date.')

        if predicted_end_date in final_x_axis:
            self.write_date_line(
                max_total, predicted_end_date, colours["Predicted End Date"]
            )

    def write_date_line(self, max_total, x_axis_position_index, line_color):
        """plots date lines"""
        pyplot.vlines(
            x_axis_position_index, 0, max_total + (max_total / 6), color=line_color
        )

    def set_plot_size(self):
        figure = pyplot.gcf()

        figure.subplots_adjust(left=0.05, right=0.95, bottom=0.1, top=0.95)

        new_width = 1920.0 / figure.dpi
        new_height = new_width / 16 * 9
        figure.set_size_inches(new_width, new_height)

    def save_graph(self):
        """saves graph, creates file locations if necessary"""
        pyplot.savefig(self.png_file)
        print(f"Cumulative flow graph saved as {self.png_file}")
