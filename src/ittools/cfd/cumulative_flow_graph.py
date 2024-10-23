from __future__ import annotations

import sys
from datetime import datetime, timedelta
from functools import reduce
from math import ceil

import matplotlib.patches as patches
import matplotlib.pyplot as pyplot
import pandas
from matplotlib.lines import Line2D
from pandas import DataFrame, DatetimeIndex

from ittools.cfd.flow_data import FlowData, Trend
from ittools.config import ProjectConfig
from ittools.domain.epic import Epic
from ittools.domain.project import Project

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
        self,
        epics_dir: str,
        project_config: ProjectConfig,
        project: Project,
        png_file: str,
        report_date: datetime.date,
        trend_period: int,
    ):
        self.png_file = png_file
        self._epics_dir = epics_dir
        self._project_config = project_config
        self._project = project
        self._report_date = report_date
        self._trend_period = trend_period
        self._initial_slope = project_config.initial_slope

    def run(self, verbose: bool) -> None:
        print(f"Cumulative Flow for project {self._project_config.name}")
        print(f"  time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        flow_data = self._load_flow_data(verbose)
        print(f"  remaining issues: {flow_data.total[-1] - flow_data.done[-1]}")
        print("  trends (issues/day):")
        print(f"    current     {flow_data.current_trend.slope:4.1f}")
        optimistic_date = f" (complete {flow_data.optimistic_completion_date})" \
            if flow_data.optimistic_completion_date else ""
        print(f"    optimistic  {flow_data.optimistic_trend.slope:4.1f}{optimistic_date}")
        pessimistic_date = f" (complete {flow_data.pessimistic_completion_date})" \
            if flow_data.pessimistic_completion_date else ""
        print(f"    pessimistic {flow_data.pessimistic_trend.slope:4.1f}{pessimistic_date}")
        print()

        self._build_graph(flow_data)

        if verbose:
            print("\nTrend history:")
            for (date, slope) in zip(flow_data.dates[-len(flow_data.slope_history):], flow_data.slope_history):
                print(f"  {date}: {slope:4.1f}")

    def first_data_date(self, verbose: bool) -> str:
        flow_data = self._load_flow_data(verbose)
        return flow_data.dates[0]

    def last_data_date(self, verbose: bool) -> str:
        flow_data = self._load_flow_data(verbose)
        return flow_data.dates[-1]

    def _build_graph(self, flow_data: FlowData) -> None:
        colours = colour_schemes["default"]
        legend_elements = self._generate_legend(colours, flow_data)

        final_x_axis, final_y_axis = self._select_final_axis(flow_data)

        max_scope = max(flow_data.total)
        max_y_scale = ceil(max_scope * 1.1)

        self._write_stacked_area_graph(
            final_x_axis, final_y_axis, max_y_scale, legend_elements, colours
        )
        self._write_current_trend_line(final_x_axis, flow_data, colours)
        self._write_optimistic_trend_line(final_x_axis, flow_data, colours)
        self._write_pessimistic_trend_line(final_x_axis, flow_data, colours)
        end_date = flow_data.pessimistic_completion_date
        if end_date:
            self._write_milestone_dates(
                max(flow_data.total), final_x_axis, end_date, colours
            )
        self._set_plot_size()

        pyplot.gcf().canvas.draw()

        self._save_graph()

    def _load_flow_data(self, verbose: bool) -> FlowData:
        epic_datas = [self._load_epic_data(epic, verbose) for epic in self._project.epics]
        project_data = reduce(self._combine_progress_data, epic_datas)
        return FlowData(
            data_frame=project_data,
            today=self._report_date,
            trend_period=self._trend_period,
            initial_slope=self._initial_slope)

    def _load_epic_data(self, epic: Epic, verbose: bool) -> DataFrame:
        csv_file = f"{self._epics_dir}/{epic.key}/progress.csv"
        if verbose:
            print(f"Reading progress from {csv_file}")
        return pandas.read_csv(csv_file, usecols=["date", "pending", "in_progress", "done", "total"], index_col="date")

    @staticmethod
    def _combine_progress_data(left: DataFrame, right: DataFrame) -> DataFrame:
        return left.combine(right, lambda left_cell, right_cell: left_cell + right_cell, fill_value=0)

    def _select_final_axis(self, flow_data: FlowData) -> tuple[DatetimeIndex, list[list[int]]]:
        start_date = flow_data.dates[0]
        end_date = self._calc_end_date(flow_data)

        final_x_axis = pandas.date_range(start_date, end_date).date.tolist()

        required_size = len(final_x_axis)
        final_y_axis = [
            self._normalise_series(flow_data.done, required_size),
            self._normalise_series(flow_data.in_progress, required_size),
            self._normalise_series(flow_data.pending, required_size),
        ]
        return final_x_axis, final_y_axis

    def _final_milestone_date(self) -> str | None:
        if not self._project_config.milestones:
            return None

        final_milestone = self._project_config.milestones[-1]
        return final_milestone["date"]

    def _calc_end_date(self, flow_data):
        milestone_date = self._final_milestone_date()
        predicted_end_date = self._last_milestone_or_end_date(flow_data, milestone_date)
        if not milestone_date:
            # No milestones define, just go to the predicted end date
            return predicted_end_date + timedelta(days=2)

        if (predicted_end_date - milestone_date).days < 15:
            # if final milestone and predicted finish are relatively close show both
            end_date = max(predicted_end_date, milestone_date) + timedelta(days=2)
        else:
            end_date = milestone_date + timedelta(days=15)
        return end_date

    @staticmethod
    def _last_milestone_or_end_date(flow_data, milestone_date):
        return (
            flow_data.pessimistic_completion_date
            or flow_data.optimistic_completion_date
            or milestone_date
        )

    @staticmethod
    def _normalise_series(series_values: list[int], required_size: int) -> list[int]:
        result = series_values[:]
        while len(result) < required_size:
            result.append(series_values[-1])

        return result

    def _generate_legend(self, colours, flow_data):
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
                label=f"{self._report_date} (Today)",
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
        for milestone in self._project_config.milestones:
            legend_elements.append(
                Line2D(
                    [0],
                    [0],
                    color=colours["Milestone"],
                    label=f"{milestone['date']} ({milestone['name']})",
                )
            )

        return legend_elements

    def _write_stacked_area_graph(
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
        pyplot.title(self._project_config.name, pad=9, fontsize=16)
        pyplot.gca().margins(0, 0)

    def _write_current_trend_line(self, final_x_axis: DatetimeIndex, flow_data: FlowData, colours: dict[str, str]):
        """Plots linear regression line"""
        start_date = self._report_date + timedelta(days=-flow_data.trend_period + 1)
        if start_date < final_x_axis[0]:
            start_date = final_x_axis[0]
        end_date = self._report_date
        self._write_trend_line(final_x_axis, colours, start_date, end_date, flow_data.current_trend)

    def _write_optimistic_trend_line(self, final_x_axis, flow_data, colours):
        """Plots linear regression line"""
        start_date = self._report_date
        end_date = final_x_axis[-1]
        self._write_trend_line(final_x_axis, colours, start_date, end_date, flow_data.optimistic_trend)

    def _write_pessimistic_trend_line(self, final_x_axis, flow_data, colours):
        """Plots linear regression line"""
        start_date = self._report_date
        end_date = final_x_axis[-1]
        self._write_trend_line(final_x_axis, colours, start_date, end_date, flow_data.pessimistic_trend)

    @staticmethod
    def _write_trend_line(
            final_x_axis: DatetimeIndex,
            colours: dict[str, str],
            start_date: datetime.date,
            end_date: datetime.date,
            trend: Trend) -> None:
        """Plots linear regression line"""
        trend_dates = pandas.date_range(start_date, end_date).date.tolist()

        start_index = final_x_axis.index(start_date)
        end_index = final_x_axis.index(end_date)

        x_values = range(start_index, end_index + 1)
        y_values = trend.slope * x_values + trend.intercept
        pyplot.plot(trend_dates, y_values, color=colours["Trendline"])

    def _write_milestone_dates(
        self, max_total, final_x_axis, predicted_end_date, colours
    ):
        """checks for existence of data + calls writing func"""
        self._write_date_line(max_total, self._report_date, colours["Current Date"])
        if self._project_config.milestones is not None:
            for i in range(len(self._project_config.milestones)):
                milestone = self._project_config.milestones[i]
                if milestone["date"] in final_x_axis:
                    self._write_date_line(
                        max_total, milestone["date"], colours["Milestone"]
                    )
                else:
                    sys.exit(f'Error: Milestone "{milestone["date"]}" has no date.')

        if predicted_end_date in final_x_axis:
            self._write_date_line(
                max_total, predicted_end_date, colours["Predicted End Date"]
            )

    def _write_date_line(self, max_total, x_axis_position_index, line_color):
        """plots date lines"""
        pyplot.vlines(
            x_axis_position_index, 0, max_total + (max_total / 6), color=line_color
        )

    def _set_plot_size(self):
        figure = pyplot.gcf()

        figure.subplots_adjust(left=0.05, right=0.95, bottom=0.1, top=0.95)

        new_width = 1920.0 / figure.dpi
        new_height = new_width / 16 * 9
        figure.set_size_inches(new_width, new_height)

    def _save_graph(self):
        """saves graph, creates file locations if necessary"""
        pyplot.savefig(self.png_file)
        print(f"Cumulative flow graph saved as {self.png_file}")
