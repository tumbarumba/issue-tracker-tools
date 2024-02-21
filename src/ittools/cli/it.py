#! /usr/bin/env python
import os
import pkg_resources
import sys
import webbrowser
from datetime import date
from typing import List

import click

from ittools.cfd.cfd_db import store_project_counts
from ittools.config import load_issue_tracker_config, ReportOptions
from ittools.domain.project import Project
from ittools.jira.jira_ext import JiraServer, JiraEpic
from ittools.reports.report_epics import EpicReport
from ittools.reports.report_issue_detail import IssueDetailReport
from ittools.reports.report_project import ProjectReport
from ittools.reports.report_release_notes import ReleaseNotesReport
from ittools.reports.report_resolved import ResolvedReport
from ittools.reports.report_in_progress import InProgressReport

DEFAULT_CONFIG_FILE = "~/issuetracker.yml"


def show_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    version = pkg_resources.require("issue-tracker-tools")[0].version
    print(f"Issue tracker tools, version {version}")
    sys.exit(0)


@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
@click.option(
    "--version",
    is_flag=True,
    callback=show_version,
    expose_value=False,
    is_eager=True,
    help="Display version information",
)
@click.option("-v", "--verbose", is_flag=True)
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True),
    help="Location of config file (default: ~/issuetracker.yml)",
)
@click.pass_context
def issue_tracker(
    ctx: click.Context,
    verbose: bool,
    config: click.Path,
) -> None:
    """Issue tracker reports and information"""
    ctx.obj = build_report_options(verbose, config)


def build_report_options(verbose: bool, config_file: click.Path) -> ReportOptions:
    config_file = config_file or os.path.expanduser(DEFAULT_CONFIG_FILE)
    if verbose:
        print(f"Using config file '{config_file}'")
    config = load_issue_tracker_config(config_file)
    return ReportOptions(config, verbose)


def load_epics(server: JiraServer, project: str, epic_keys: List[str]) -> List[JiraEpic]:
    if project:
        return server.query_project_epics(project)
    else:
        return [server.jira_epic(key) for key in epic_keys]


@issue_tracker.command()
@click.option("-p", "--project", default=None)
@click.argument("epic_keys", nargs=-1)
@click.pass_context
def epic_summary(ctx: click.Context, project: str, epic_keys: List[str]) -> None:
    """Report on stories within epics."""
    options: ReportOptions = ctx.obj
    server = JiraServer(options.verbose, options.jira_config)
    epics = load_epics(server, project, epic_keys)
    if not epics:
        ctx.fail("Either project or epic key(s) must be specified")
    EpicReport(options, server).run(epics)


@issue_tracker.command()
@click.option("-e", "--epic", is_flag=True, default=False, help="Group issues by epic")
@click.option("-t", "--team", is_flag=True, default=False, help="Group issues by team")
@click.pass_context
def in_progress(ctx: click.Context, epic: bool, team: bool) -> None:
    """Report on issues currently in progress."""
    options: ReportOptions = ctx.obj
    server = JiraServer(options.verbose, options.jira_config)
    InProgressReport(options, server).run(epic, team)


def add_fix_version(
    server: JiraServer, issue_keys: List[str], new_fix_version: str
) -> None:
    for key in issue_keys:
        jira_issue = server.jira_issue(key)
        if new_fix_version in jira_issue.fix_versions():
            print(f"{jira_issue.key}: already assigned to {new_fix_version}")
        else:
            jira_issue.add_fix_version(new_fix_version)
            print(f"{jira_issue.key}: added version {new_fix_version}")


@issue_tracker.command()
@click.option(
    "-o", "--open", is_flag=True, default=False, help="Open issue in a web browser"
)
@click.option(
    "-f",
    "--update-fix-version",
    is_flag=False,
    type=click.STRING,
    help="Update issue with specified fix version",
)
@click.argument("issue_keys", nargs=-1)
@click.pass_context
def issue(
    ctx: click.Context, open: bool, update_fix_version: str, issue_keys: List[str]
) -> None:
    """Report on issue detail."""
    if not issue_keys:
        sys.exit("issue key required")

    options: ReportOptions = ctx.obj
    server = JiraServer(options.verbose, options.jira_config)

    if open:
        webbrowser.open(f"{options.jira_config.url}/browse/{issue_keys[0]}")
    elif update_fix_version:
        add_fix_version(server, issue_keys, update_fix_version)
    else:
        IssueDetailReport(server, options.verbose).run(issue_keys)


@issue_tracker.command()
@click.argument("project")
@click.pass_context
def project(ctx: click.Context, project: str) -> None:
    """Report on progress for a project."""
    options: ReportOptions = ctx.obj
    report_date = str(date.today())
    jira_server = JiraServer(options.verbose, options.jira_config)
    project_data = Project.load(jira_server, project)
    ProjectReport(project_data).run(report_date)
    store_project_counts(report_date, project_data, options)


@issue_tracker.command()
@click.option(
    "-f",
    "--fix-version",
    is_flag=False,
    type=click.STRING,
    default=None,
    help="Include all issues with this fix version",
)
@click.option("-t", "--no-tasks", is_flag=True, default=False, help="Exclude tasks")
@click.option(
    "-m", "--markdown", is_flag=True, default=False, help="Output report as markdown"
)
@click.argument("issue_keys", nargs=-1)
@click.pass_context
def release(
    ctx: click.Context,
    fix_version: str,
    no_tasks: bool,
    markdown: bool,
    issue_keys: List[str],
) -> None:
    """Describes a list of tickets as release notes"""
    options: ReportOptions = ctx.obj
    server = JiraServer(options.verbose, options.jira_config)

    if fix_version:
        fix_issues = server.query_fix_version(fix_version)
        issue_keys = [issue.key for issue in fix_issues]

    if not issue_keys:
        sys.exit("issue keys required for release report")

    ReleaseNotesReport(options, server, no_tasks, markdown).run(issue_keys)


@issue_tracker.command()
@click.option(
    "-d",
    "--days",
    type=click.INT,
    help="include issues resovled this many days prior to today",
)
@click.option(
    "-f",
    "--from",
    "from_date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="include resolved issues from this date onwards",
)
@click.option(
    "-t",
    "--to",
    "to_date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="include issues resolved before this date",
)
@click.option(
    "-l",
    "--label",
    "label",
    type=click.STRING,
    help="filter issues to epics with this label"
)
@click.option(
    "--team",
    "team",
    type=click.STRING,
    help="filter issues those completed by the given team"
)
@click.pass_context
def resolved(
    ctx: click.Context, days: int, from_date: click.DateTime, to_date: click.DateTime, label: str, team: str
) -> None:
    """Report on recently closed issues."""
    options: ReportOptions = ctx.obj
    server = JiraServer(options.verbose, options.jira_config)

    if from_date:
        from_date = from_date.date()
    if to_date:
        to_date = to_date.date()

    if team:
        team_members = options.teams.get(team, list())
        if not team_members:
            raise ValueError(f"No members in team '{team}'")
    else:
        team_members = []

    ResolvedReport(options, server).run(days, from_date, to_date, label, team, team_members)


@issue_tracker.command()
@click.argument("label")
@click.pass_context
def jql_label(ctx: click.Context, label: str) -> None:
    """Generate jql to search issues for epics with a given label"""
    options: ReportOptions = ctx.obj
    server = JiraServer(options.verbose, options.jira_config)
    jql = f"project = DS AND type = Epic AND 'Epic Status' != Done AND labels = {label} order by key"
    issues = server.query_jql_issues(jql)
    keys = [issue.key for issue in issues]
    print(f"'Epic Link' in ({', '.join(keys)})")


if __name__ == "__main__":
    try:
        issue_tracker()
        sys.exit(0)
    except Exception as e:
        sys.stderr.write(f"Command failed: {getattr(e, 'message', repr(e))}")
        sys.exit(1)
