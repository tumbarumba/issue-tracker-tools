#! /usr/bin/env python
import click
import os
import os.path
import datetime
import sys

from ittools.cfd.flow_data import FlowData
from ittools.config import load_issue_tracker_config, load_project_config, IssueTrackerConfig, ProjectConfig
from ittools.cfd.cumulative_flow_graph import CumulativeFlowGraph
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
    if not (project_label or epic):
        click.get_current_context().fail("one of project label or epic must be specified")
    if project_label and epic:
        click.get_current_context().fail("only one of project label or epic can be specified")

    cfd_report = _make_cfd_report(config, days, epic, project_label, today, verbose)
    if show_first_date:
        print(cfd_report.first_data_date(verbose))
    elif show_last_date:
        print(cfd_report.last_data_date(verbose))
    else:
        cfd_report.run(verbose)
        if open_graph:
            os.system(f"xdg-open '{cfd_report.png_file}'")


def _make_cfd_report(
        config_path: click.Path,
        trend_period: int,
        epic_key: str,
        project_label: str,
        today: click.DateTime,
        verbose: bool
) -> CumulativeFlowGraph:
    config = make_it_config(verbose, config_path)
    jira_server = JiraServer(verbose, config.jira_config)
    report_date = date_option_or_today(today)
    if project_label:
        return _make_project_cfd(project_label, trend_period, config.report_dir, jira_server, report_date, verbose)
    else:
        return _make_epic_cfd(epic_key, trend_period, config.report_dir, jira_server, report_date, verbose)


def _make_project_cfd(
        project_label: str,
        trend_period: int,
        report_dir: str,
        jira_server: JiraServer,
        report_date: datetime.date,
        verbose: bool
) -> CumulativeFlowGraph:
    project_config = make_project_config(verbose, report_dir, project_label)
    project = Project.load(jira_server, project_label)
    png_file = f"{report_dir}/{project_label}/cfd-{str(report_date)}.png"
    return CumulativeFlowGraph(f"{report_dir}/epics", project_config, project, png_file, report_date, trend_period)


def _make_epic_cfd(
        epic_key: str,
        trend_period: int,
        report_dir: str,
        jira_server: JiraServer,
        report_date: datetime.date,
        verbose: bool
) -> CumulativeFlowGraph:
    jira_epic = jira_server.jira_epic(epic_key)
    project_config = make_project_config(verbose, report_dir, f"{epic_key}: {jira_epic.summary}")
    project = Project(epic_key, [jira_epic])
    png_file = f"{report_dir}/epics/{epic_key}/cfd-{str(report_date)}.png"
    return CumulativeFlowGraph(f"{report_dir}/epics", project_config, project, png_file, report_date, trend_period)


def make_it_config(verbose: bool, config_file: click.Path) -> IssueTrackerConfig:
    config_file = config_file or os.path.expanduser(DEFAULT_CONFIG_FILE)
    if verbose:
        print(f"Using issue tracker config file '{config_file}'")
    return load_issue_tracker_config(config_file)


def make_project_config(verbose: bool, report_dir: str, project_label: str) -> ProjectConfig:
    config_file = f"{report_dir}/{project_label}/project.yml"
    if os.path.isfile(config_file):
        if verbose:
            print(f"Using project config file '{config_file}'")
        return load_project_config(config_file)
    else:
        if verbose:
            print(f"Project config file missing ('{config_file}'), using default")
        return ProjectConfig({"name": project_label, "key": project_label, })


def date_option_or_today(option: click.DateTime) -> datetime.date:
    if option:
        return option.date()
    return datetime.date.today()


if __name__ == "__main__":
    try:
        cfd()
        sys.exit(0)
    except Exception as e:
        sys.stderr.write(f"Command failed: {getattr(e, 'message', repr(e))}")
        sys.exit(1)
