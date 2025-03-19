#! /usr/bin/env python
import traceback
from functools import reduce
from pathlib import Path

import click
import os
import os.path
import datetime
import sys

import pandas
from pandas import DataFrame

from ittools.cfd.flow_data import FlowData
from ittools.config import IssueTrackerConfig, ProjectConfig
from ittools.cfd.cumulative_flow_graph import CumulativeFlowGraph
from ittools.domain.epic import Epic
from ittools.domain.project import Project
from ittools.jira.jira_ext import JiraServer

DEFAULT_CONFIG_FILE = "~/issuetracker.yml"


@click.command(context_settings=dict(help_option_names=["-h", "--help"]))
@click.option(
    "-t",
    "--today",
    default=None,
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Override today's date",
)
@click.option(
    "-d",
    "--days",
    default=FlowData.DEFAULT_TREND_PERIOD,
    type=click.INT,
    help=f"Number of days to calculate trends (default: {FlowData.DEFAULT_TREND_PERIOD})",
)
@click.option("-p", "--project-label", "--project", help="Project label")
@click.option("-e", "--epic", help="Epic key")
@click.option("-x", "--excel", type=click.Path(), help="Excel file")
@click.option("-f", "--show-first-date", is_flag=True, help="Show first date in report data")
@click.option("-l", "--show-last-date", is_flag=True, help="Show last date in report data")
@click.option("-c", "--config", type=click.Path(exists=True))
@click.option("-o", "--open-graph", is_flag=True, default=False, help="Open the graph after generation")
@click.option("-v", "--verbose", is_flag=True, help="Show extra information from report")
def cfd(
    today: click.DateTime,
    days: click.INT,
    project_label: str,
    epic: str,
    excel: click.Path,
    show_first_date: bool,
    show_last_date: bool,
    config: click.Path,
    open_graph: bool,
    verbose: bool
) -> None:
    """Create a cumulative flow diagram for a given project

    Requires a project progress file (progress.csv) in the project directory. This is normally generated
    by the `it project` command
    """
    if not (project_label or epic or excel):
        click.get_current_context().fail("one of project label or epic must be specified")
    if project_label and epic:
        click.get_current_context().fail("only one of project label or epic can be specified")

    cfd_report = _make_cfd_report(config, days, epic, project_label, excel, today, verbose)
    if show_first_date:
        print(cfd_report.first_data_date())
    elif show_last_date:
        print(cfd_report.last_data_date())
    else:
        cfd_report.run(verbose)
        if open_graph:
            os.system(f"xdg-open '{cfd_report.png_file}'")


def _make_cfd_report(
        config_path: click.Path,
        trend_period: int,
        epic_key: str,
        project_label: str,
        excel_file: click.Path,
        today: click.DateTime,
        verbose: bool
) -> CumulativeFlowGraph:
    report_date = _date_option_or_today(today)
    if excel_file:
        return _make_excel_cfd(excel_file, report_date, verbose)

    config = _make_it_config(verbose, config_path)
    jira_server = JiraServer(verbose, config.jira_config)
    if project_label:
        return _make_project_cfd(project_label, trend_period, config.report_dir, jira_server, report_date, verbose)
    else:
        return _make_epic_cfd(epic_key, trend_period, config.report_dir, jira_server, report_date, verbose)


def _make_excel_cfd(excel_file: click.Path, report_date: datetime.date, verbose: bool) -> CumulativeFlowGraph:
    if verbose:
        print(f"Reading progress from {excel_file}")
    data_frame = pandas.read_excel(excel_file)
    flow_data = FlowData(
        data_frame=data_frame,
        today=report_date,
        trend_period=FlowData.DEFAULT_TREND_PERIOD,
        initial_slope=FlowData.DEFAULT_SLOPE
    )
    project_config = ProjectConfig({"name": os.path.basename(str(excel_file))})
    png_file = Path(str(excel_file)).parent / f"cfd-{str(report_date)}.png"
    return CumulativeFlowGraph(flow_data, project_config, str(png_file), report_date)


def _make_project_cfd(
        project_label: str,
        trend_period: int,
        report_dir: str,
        jira_server: JiraServer,
        report_date: datetime.date,
        verbose: bool
) -> CumulativeFlowGraph:
    project_config = _make_project_config(verbose, report_dir, project_label)
    project = Project.load(jira_server, project_label)
    data_frame = _data_frame_from_project(project, f"{report_dir}/epics", verbose)
    flow_data = FlowData(
        data_frame=data_frame,
        today=report_date,
        trend_period=trend_period,
        initial_slope=project_config.initial_slope
    )
    png_file = f"{report_dir}/{project_label}/cfd-{str(report_date)}.png"
    return CumulativeFlowGraph(flow_data, project_config, png_file, report_date)


def _make_epic_cfd(
        epic_key: str,
        trend_period: int,
        report_dir: str,
        jira_server: JiraServer,
        report_date: datetime.date,
        verbose: bool
) -> CumulativeFlowGraph:
    jira_epic = jira_server.jira_epic(epic_key)
    project_config = _make_project_config(verbose, report_dir, f"{epic_key}: {jira_epic.summary}")
    project = Project(epic_key, [jira_epic])
    data_frame = _data_frame_from_project(project, f"{report_dir}/epics", verbose)
    flow_data = FlowData(
        data_frame=data_frame,
        today=report_date,
        trend_period=trend_period,
        initial_slope=project_config.initial_slope
    )
    png_file = f"{report_dir}/epics/{epic_key}/cfd-{str(report_date)}.png"
    return CumulativeFlowGraph(flow_data, project_config, png_file, report_date)


def _make_it_config(verbose: bool, config_file: click.Path) -> IssueTrackerConfig:
    config_file = config_file or os.path.expanduser(DEFAULT_CONFIG_FILE)
    if verbose:
        print(f"Using issue tracker config file '{config_file}'")
    return IssueTrackerConfig.load(config_file)


def _make_project_config(verbose: bool, report_dir: str, project_label: str) -> ProjectConfig:
    config_file = f"{report_dir}/{project_label}/project.yml"
    if os.path.isfile(config_file):
        if verbose:
            print(f"Using project config file '{config_file}'")
        return ProjectConfig.load(config_file)
    else:
        if verbose:
            print(f"Project config file missing ('{config_file}'), using default")
        return ProjectConfig({"name": project_label, "key": project_label, })


def _data_frame_from_project(project: Project, epics_dir: str, verbose: bool) -> DataFrame:
    epic_datas = [_load_epic_data(epic, epics_dir, verbose) for epic in project.epics]
    project_data = reduce(_combine_progress_data, epic_datas)
    return project_data


def _load_epic_data(self, epic: Epic, epics_dir: str, verbose: bool) -> DataFrame:
    csv_file = f"{epics_dir}/{epic.key}/progress.csv"
    if verbose:
        print(f"Reading progress from {csv_file}")
    return pandas.read_csv(csv_file, usecols=["date", "pending", "in_progress", "done", "total"], index_col="date")


def _combine_progress_data(left: DataFrame, right: DataFrame) -> DataFrame:
    return left.combine(right, lambda left_cell, right_cell: left_cell + right_cell, fill_value=0)


def _date_option_or_today(option: click.DateTime) -> datetime.date:
    if option:
        return option.date()
    return datetime.date.today()


if __name__ == "__main__":
    try:
        cfd()
        sys.exit(0)
    except Exception as e:
        print(traceback.format_exc())
        sys.stderr.write(f"Command failed: {getattr(e, 'message', repr(e))}")
        sys.exit(1)
