from __future__ import annotations

import re
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
    def __init__(self, epic: JiraEpic, issues: List[JiraIssue]):
        self.epic = epic
        self.issues: List[JiraIssue] = sorted(issues, key=lambda issue: issue.key)

    @property
    def epic_key(self) -> str:
        return self.epic.key

    @property
    def epic_summary(self) -> str:
        return self.epic.summary


class Project:
    def __init__(self, label: str):
        self.label = label
        self.epics: Dict[str, EpicIssues] = {}

    def add_epic(self, epic: JiraEpic, issues: List[JiraIssue]) -> None:
        self.epics[epic.key] = EpicIssues(epic, issues)

    @property
    def issues(self) -> List[JiraIssue]:
        return [issue for epic_issues in self.epics.values() for issue in epic_issues.issues]

    @property
    def issue_durations(self) -> List[float]:
        return [issue.duration for issue in self.issues]


class IssueSummaryReport:
    def __init__(
            self,
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

    def run(self, report_issues: List[JiraIssue]) -> None:
        if not report_issues:
            print("No issues found")
            return

        issues_without_epics = [issue.key for issue in report_issues if not issue.epic_key]
        if issues_without_epics:
            print("Unable to run report while there are issues without epics:")
            print(f"\t{', '.join(issues_without_epics)}")
            return

        projects = self.build_projects(report_issues)

        for project_label in sorted(projects):
            self.report_project(projects[project_label])

        if self.markdown:
            issues_with_special_instructions = [issue for issue in report_issues if issue.has_release_notes]
            if issues_with_special_instructions:
                print_special_instructions(issues_with_special_instructions)

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

    def build_projects(
            self, report_issues: List[JiraIssue]
    ) -> Dict[str, Project]:
        projects: Dict[str, Project] = {}
        report_issues.sort(key=lambda issue: issue.epic_key)
        for epic_key, epic_issues in groupby(
                report_issues, lambda issue: issue.epic_key
        ):
            epic: JiraEpic = self.jira.jira_epic(epic_key)
            project_label = _project_for(epic.labels)
            project = projects.get(project_label) or Project(project_label)
            projects[project_label] = project
            project.add_epic(epic, list(epic_issues))

        return projects

    def report_project(self, project: Project) -> None:
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

    def print_heading_l1(self, heading: str) -> None:
        if self.markdown:
            print(f"## {heading}")
        else:
            print(heading)
            print(len(heading) * "=")

        print()

    def print_heading_epic(self, epic: JiraEpic) -> None:
        if self.markdown:
            print(f"### {epic.summary} ([{epic.key}]({epic.url}))")
            print()
        else:
            print(f"Epic {epic.key}: {epic.summary}")

    def print_issue(self, issue: JiraIssue) -> None:
        issue_icon = self.type_display[issue.issue_type]
        release_notes_flag = _release_notes_flag(issue)

        if self.markdown:
            print(f"* {issue_icon} [{issue.key}]({issue.url}): {issue.summary}{release_notes_flag}")
        else:
            if self.show_stats:
                duration = f"{issue.duration:5.2f} "
            else:
                duration = ""
            print(f"[{duration}{issue_icon}] {issue.key}: {issue.summary} ({issue.assignee})")


def print_statistics(title: str, issues: List[JiraIssue]) -> None:
    durations = [issue.duration for issue in issues]
    print(f"Statistics: {title}")
    print(f" issue count:     : {len(durations):2}")
    print(f" cycle time total : {sum(durations):5.2f}")
    print(f" cycle time mean  : {mean(durations):5.2f}")
    print(f" cycle time median: {median(durations):5.2f}")
    print("")
    print("Cycle time breakdown (calendar days):")
    in_progress_time = _total_time_in_state(issues, "In Progress")
    in_review_time = _total_time_in_state(issues, "In Review")
    under_test_time = _total_time_in_state(issues, "Under Test")
    total_time = in_progress_time + in_review_time + under_test_time
    print(f" in progress: {in_progress_time:7.2f} ({in_progress_time / total_time * 100:3.0f}%)")
    print(f" in review  : {in_review_time:7.2f} ({in_review_time / total_time * 100:3.0f}%)")
    print(f" under test : {under_test_time:7.2f} ({under_test_time / total_time * 100:3.0f}%)")
    print(" ---------------------------")
    print(f" total      : {total_time:7.2f} (100%)")


def print_special_instructions(issues_with_special_instructions: List[JiraIssue]):
    print("\n## <sup>¶</sup> Special Instructions\n")
    for issue in issues_with_special_instructions:
        print(f"### {issue.summary} ([{issue.key}]({issue.url}))")
        print("")
        print(_extract_special_instructions(issue))
        print("")


def _extract_special_instructions(issue: JiraIssue):
    description = issue.description
    if not re.search("release notes", description, re.IGNORECASE):
        return description

    # Only show text in the description after "Release Notes"
    found_release_notes = False
    instructions = ""
    for line in description.splitlines(keepends=True):
        if found_release_notes:
            instructions += line
        elif re.search("release notes", line, re.IGNORECASE):
            found_release_notes = True

    return instructions


def _total_time_in_state(issues: List[JiraIssue], state_name: str) -> float:
    return sum(issue.time_in_state(state_name) for issue in issues)


def _project_for(labels: List[str]) -> str:
    for label in labels:
        if _is_project(label):
            return label.split("_")[0]
    return "Unplanned"


def _is_project(label: str) -> bool:
    return "Team" not in label


def _release_notes_flag(issue: JiraIssue):
    if issue.has_release_notes:
        return "<sup>¶</sup>"
    else:
        return ""
