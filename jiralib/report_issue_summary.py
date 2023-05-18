from __future__ import annotations
from typing import Dict, List
import sys
import datetime
from statistics import mean, median
from itertools import groupby
from jira import Issue, JIRA
from .jira_issue import JiraIssue

this = sys.modules[__name__]
this.date_source = datetime.date


class EpicIssues:
    def __init__(self: EpicIssues, epic_key: str, epic_summary: str, issues: List[JiraIssue]):
        self.epic_key: str = epic_key
        self.epic_summary: str = epic_summary
        self.issues: List[JiraIssue] = issues


class Project:
    def __init__(self: Project, label: str):
        self.label = label
        self.epics: Dict[str, EpicIssues] = {}
        self.durations: List[float] = []

    def add_epic(self: Project, epic: Issue, issues: List[JiraIssue]) -> None:
        epic_issues = EpicIssues(epic.key, epic.fields.summary, issues)
        self.epics[epic.key] = epic_issues
        self.durations.extend(list(map(lambda issue: issue.duration, issues)))


class IssueSummaryReport:
    def __init__(self: IssueSummaryReport, opts: Dict[object], jira: JIRA, show_stats: bool):
        self.verbose: bool = opts.verbose
        self.show_stats: bool = show_stats
        self.jira: JIRA = jira
        self.type_display: Dict[str, str] = {
            issuetype["name"]: issuetype["display"] for index, issuetype in enumerate(opts.jira_config.issuetypes)
        }

    def run(self: IssueSummaryReport, report_issues: List[JiraIssue]) -> None:
        if not report_issues:
            print("No issues found")
            return

        projects = self.build_projects(report_issues)

        for project_label in sorted(projects):
            self.report_project(projects[project_label])

        if self.show_stats:
            all_durations = self.collect_durations(projects)
            print_heading("All Projects")
            print_statistics("all issues", all_durations)

            total_count = len(all_durations)
            for project_label in sorted(projects):
                project_count = len(projects[project_label].durations)
                print(f" {project_count:3} ({project_count / total_count * 100:2.0f}%): {project_label}")

            print(" issue durations")
            total_duration = sum(all_durations)
            for project_label in sorted(projects):
                project_duration = sum(projects[project_label].durations)
                print(f"  {project_duration:6.2f} ({project_duration / total_duration * 100:3.0f}%): {project_label}")
            print(" --------------------")
            print(f"  {total_duration:6.2f} (100%): Total")

    def build_projects(self: IssueSummaryReport, report_issues: List[JiraIssue]) -> Dict[str, Project]:
        projects: Dict[str, Project] = {}
        report_issues.sort(key=lambda issue: issue.epic_key())
        for epic_key, epic_issues in groupby(report_issues, lambda issue: issue.epic_key()):
            epic: Issue = self.jira.issue(epic_key)
            project_label = project_for(epic.fields.labels)
            project = projects.get(project_label) or Project(project_label)
            projects[project_label] = project
            project.add_epic(epic, list(epic_issues))

        return projects

    def collect_durations(self: IssueSummaryReport, projects: Dict[str, Project]) -> List[float]:
        all_durations: List[float] = []
        for project_label in sorted(projects):
            project = projects[project_label]
            all_durations.extend(project.durations)

        return all_durations

    def report_project(self: IssueSummaryReport, project: Project) -> None:
        print_heading(f"Project: {project.label}")

        for epic_key in sorted(project.epics):
            ei: EpicIssues = project.epics[epic_key]
            print(f"Epic {ei.epic_key}: {ei.epic_summary}")
            for issue in ei.issues:
                issueicon = self.type_display[issue.jira_issue.fields.issuetype.name]
                if self.show_stats:
                    duration = f"{issue.duration:5.2f} "
                else:
                    duration = ""
                print(f"[{duration}{issueicon}] {issue.key}: {issue.summary}")
                if self.verbose:
                    print(f"           started:   {issue.start_time()}")
                    print(f"           completed: {issue.completed_time()}")
            print()

        if self.show_stats:
            print_statistics(f"project {project.label}", project.durations)
            print()


def print_heading(heading) -> None:
    print(heading)
    print(len(heading) * "=")
    print()


def print_statistics(title: str, durations: List[float]) -> None:
    print(f"Statistics: {title}")
    print(f" lead time mean  : {mean(durations):5.2f}")
    print(f" lead time median: {median(durations):5.2f}")
    print(f" lead time total : {sum(durations):5.2f}")
    print(f" issue count:    : {len(durations):2}")


def project_for(labels: List[str]) -> str:
    for label in labels:
        if is_project(label):
            return label.split("_")[0]
    return "Unplanned"


def is_project(label: str) -> bool:
    return "Team" not in label
