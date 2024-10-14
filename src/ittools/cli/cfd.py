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
@click.option("-v", "--verbose", is_flag=True)
@click.option("-c", "--config", type=click.Path(exists=True))
@click.option(
    "-o",
    "--open-graph",
    is_flag=True,
    default=False,
    help="Open the graph after generation",
)
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
@click.option(
    "-p", "--project-label", "--project",
    help="Project label",
)
@click.option(
    "-e", "--epic",
    help="Epic key",
)
def cfd(
    verbose: bool,
    config: click.Path,
    open_graph: bool,
    today: click.DateTime,
    days: click.INT,
    project_label: str,
    epic: str,
) -> None:
    """Create a cumulative flow diagram for a given project

    Requires a project progress file (progress.csv) in the project directory. This is normally generated
    by the `it project` command
    """
    it_config = make_it_config(verbose, config)
    jira_server = JiraServer(verbose, it_config.jira_config)
    report_date = date_option_or_today(today)
    epic_dir = f"{it_config.report_dir}/epics"
    if project_label:
        _make_project_cfd(days, epic_dir, it_config, jira_server, open_graph, project_label, report_date, verbose)
    elif epic:
        _make_epic_cfd(days, epic, epic_dir, it_config, jira_server, open_graph, report_date, verbose)
    else:
        click.get_current_context().fail("one of project label or epic must be specified")


def _make_project_cfd(days, epic_dir, it_config, jira_server, open_graph, project_label, report_date, verbose):
    project_config = make_project_config(verbose, it_config.report_dir, project_label)
    project = Project.load(jira_server, project_label)
    png_file = f"{it_config.report_dir}/{project_label}/cfd-{str(report_date)}.png"
    CumulativeFlowGraph(epic_dir, project_config, project, png_file, report_date, days).run(verbose, open_graph)


def _make_epic_cfd(days, epic, epic_dir, it_config, jira_server, open_graph, report_date, verbose):
    jira_epic = jira_server.jira_epic(epic)
    project_config = make_project_config(verbose, it_config.report_dir, f"{epic}: {jira_epic.summary}")
    project = Project(epic, [jira_epic])
    png_file = f"{it_config.report_dir}/epics/{epic}/cfd-{str(report_date)}.png"
    CumulativeFlowGraph(epic_dir, project_config, project, png_file, report_date, days).run(verbose, open_graph)


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
