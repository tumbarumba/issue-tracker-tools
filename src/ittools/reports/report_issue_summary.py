from __future__ import annotations
from typing import Dict, List
import sys
import datetime
from statistics import mean, median
from itertools import groupby

from ittools.config import ReportOptions
from ittools.jira.jira_ext import JiraIssue, JiraEpic, JiraServer

this = sys.modules[__name__]
this.date_source = datetime.date


class EpicIssues:
    def __init__(self: EpicIssues, epic: JiraEpic, issues: List[JiraIssue]):
        self.epic = epic
        self.issues: List[JiraIssue] = sorted(issues, key=lambda issue: issue.key)

    @property
    def epic_key(self: EpicIssues) -> str:
        return self.epic.key

    @property
    def epic_summary(self: EpicIssues) -> str:
        return self.epic.summary


class Project:
    def __init__(self: Project, label: str):
        self.label = label
        self.epics: Dict[str, EpicIssues] = {}

    def add_epic(self: Project, epic: JiraEpic, issues: List[JiraIssue]) -> None:
        self.epics[epic.key] = EpicIssues(epic, issues)

    @property
    def issues(self: Project) -> List[JiraIssue]:
        return [issue for epic_issues in self.epics.values() for issue in epic_issues.issues]

    @property
    def issue_durations(self: Project) -> List[float]:
        return [issue.duration for issue in self.issues]


class IssueSummaryReport:
    def __init__(
        self: IssueSummaryReport,
        opts: ReportOptions,
        jira: JiraServer,
        show_stats: bool,
        markdown: bool,
    ):
        self.verbose: bool = opts.verbose
        self.show_stats: bool = show_stats
        self.markdown: bool = markdown
        self.jira: JiraServer = jira
        self.type_display: Dict[str, str] = {
            issue_type["name"]: issue_type["display"]
            for index, issue_type in enumerate(opts.jira_config.issuetypes)
        }

    def run(self: IssueSummaryReport, report_issues: List[JiraIssue]) -> None:
        if not report_issues:
            print("No issues found")
            return

        projects = self.build_projects(report_issues)

        for project_label in sorted(projects):
            self.report_project(projects[project_label])

        if self.show_stats:
            all_durations = [issue.duration for issue in report_issues]
            self.print_heading_l1("All Projects")
            print_statistics("all issues", report_issues)
            print("")
            print(" Projects by issue counts:")
            total_count = len(all_durations)
            for project_label in sorted(projects):
                project_count = len(projects[project_label].issues)
                print(
                    f" {project_count:3} ({project_count / total_count * 100:3.0f}%): {project_label}"
                )
            print(" --------------------")
            print(f" {total_count:3} (100%): Total")
            print("")
            print(" Projects by issue durations:")
            total_duration = sum(all_durations)
            for project_label in sorted(projects):
                project_duration = sum(projects[project_label].issue_durations)
                print(
                    f" {project_duration:5.1f} ({project_duration / total_duration * 100:3.0f}%): {project_label}"
                )
            print(" --------------------")
            print(f" {total_duration:5.1f} (100%): Total")

    def build_projects(
        self: IssueSummaryReport, report_issues: List[JiraIssue]
    ) -> Dict[str, Project]:
        projects: Dict[str, Project] = {}
        report_issues.sort(key=lambda issue: issue.epic_key)
        for epic_key, epic_issues in groupby(
            report_issues, lambda issue: issue.epic_key
        ):
            epic: JiraEpic = self.jira.jira_epic(epic_key)
            project_label = project_for(epic.labels)
            project = projects.get(project_label) or Project(project_label)
            projects[project_label] = project
            project.add_epic(epic, list(epic_issues))

        return projects

    def report_project(self: IssueSummaryReport, project: Project) -> None:
        self.print_heading_l1(f"Project: {project.label}")

        for epic_key in sorted(project.epics):
            ei: EpicIssues = project.epics[epic_key]
            self.print_heading_epic(ei.epic)
            for issue in ei.issues:
                self.print_issue(issue)
                if self.verbose:
                    print(f"           started:   {issue.start_time()}")
                    print(f"           completed: {issue.completed_time()}")
            print()

        if self.show_stats:
            print_statistics(f"project {project.label}", project.issues)
            print()

    def print_heading_l1(self: IssueSummaryReport, heading: str) -> None:
        if self.markdown:
            print(f"## {heading}")
        else:
            print(heading)
            print(len(heading) * "=")

        print()

    def print_heading_epic(self: IssueSummaryReport, epic: JiraEpic) -> None:
        if self.markdown:
            print(f"### {epic.summary} ([{epic.key}]({epic.url}))")
            print()
        else:
            print(f"Epic {epic.key}: {epic.summary}")

    def print_issue(self: IssueSummaryReport, issue: JiraIssue) -> None:
        issue_icon = self.type_display[issue.issue_type]

        if self.markdown:
            print(f"* {issue_icon} [{issue.key}]({issue.url}): {issue.summary}")
        else:
            if self.show_stats:
                duration = f"{issue.duration:5.2f} "
            else:
                duration = ""
            print(f"[{duration}{issue_icon}] {issue.key}: {issue.summary}")


def print_statistics(title: str, issues: List[JiraIssue]) -> None:
    durations = [issue.duration for issue in issues]
    print(f"Statistics: {title}")
    print(f" issue count:    : {len(durations):2}")
    print(f" lead time total : {sum(durations):5.2f}")
    print(f" lead time mean  : {mean(durations):5.2f}")
    print(f" lead time median: {median(durations):5.2f}")


def project_for(labels: List[str]) -> str:
    for label in labels:
        if is_project(label):
            return label.split("_")[0]
    return "Unplanned"


def is_project(label: str) -> bool:
    return "Team" not in label
