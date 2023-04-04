import sys
import datetime
from statistics import mean, median
from itertools import groupby


this = sys.modules[__name__]
this.date_source = datetime.date


class EpicIssues:
    def __init__(self, epic_key, epic_summary, issues):
        self.epic_key = epic_key
        self.epic_summary = epic_summary
        self.issues = issues


class Project:
    def __init__(self, label):
        self.label = label
        self.epics = {}
        self.durations = []

    def add_epic(self, epic, issues):
        epic_issues = EpicIssues(epic.key, epic.fields.summary, issues)
        self.epics[epic.key] = epic_issues
        self.durations.extend(list(map(lambda issue: issue.duration, issues)))


class IssueSummaryReport:
    def __init__(self, opts, jira, show_stats):
        self.verbose = opts.verbose
        self.issuetypes = opts.jira_config.issuetypes
        self.jira = jira
        self.show_stats = show_stats
        self.type_display = {
            issuetype["name"]: issuetype["display"] for index, issuetype in enumerate(opts.jira_config.issuetypes)
        }

    def run(self, report_issues):
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

            total = len(all_durations)
            for project_label in sorted(projects):
                project_count = len(projects[project_label].durations)
                print(f" {project_count:3} ({project_count / total * 100:2.0f}%): {project_label}")

    def build_projects(self, report_issues):
        projects = {}
        report_issues.sort(key=lambda issue: issue.epic_key())
        for epic_key, epic_issues in groupby(report_issues, lambda issue: issue.epic_key()):
            epic = self.jira.issue(epic_key)
            project_label = project_for(epic.fields.labels)
            project = projects.get(project_label) or Project(project_label)
            projects[project_label] = project
            project.add_epic(epic, list(epic_issues))

        return projects

    def collect_durations(self, projects):
        all_durations = []
        for project_label in sorted(projects):
            project = projects[project_label]
            all_durations.extend(project.durations)

        return all_durations

    def report_project(self, project):
        print_heading(f"Project: {project.label}")

        for epic_key in sorted(project.epics):
            ei = project.epics[epic_key]
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


def print_heading(heading):
    print(heading)
    print(len(heading) * "=")
    print()


def print_statistics(title, durations):
    print(f"Statistics: {title}")
    print(f" lead time mean  : {mean(durations):5.2f}")
    print(f" lead time median: {median(durations):5.2f}")
    print(f" issue count:    : {len(durations):2}")


def project_for(labels):
    for label in labels:
        if is_project(label):
            return label.split("_")[0]
    return "Unplanned"


def is_project(label):
    return "Team" not in label
