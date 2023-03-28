import csv
import sys
import datetime
from statistics import mean, median
from itertools import groupby
from .jira_builder import JiraQueries
from .jira_issue import JiraIssue


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


class ResolvedReport:
    def __init__(self, opts, jira):
        self.verbose = opts.verbose
        self.issuetypes = opts.jira_config.issuetypes
        self.jira = jira
        self.query = JiraQueries(jira)
        self.type_display = {
            issuetype["name"]: issuetype["display"] for index, issuetype in enumerate(opts.jira_config.issuetypes)
        }

    def run(self, days, user_from_date, user_to_date, csv_file):
        from_date = user_from_date or jira_from_date_days_ago(days)
        to_date = user_to_date or jira_to_date()
        print(f"Resolved issues after {from_date} and before {to_date}\n")
        report_issues = list(map(JiraIssue, self.query.get_resolved_issues(from_date, to_date)))
        if not report_issues:
            print("No resolved issues found")
            return

        update_issue_store(report_issues, csv_file)

        projects = self.build_projects(report_issues)

        for project_label in sorted(projects):
            self.report_project(projects[project_label])

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
                issuetype = issue.jira_issue.fields.issuetype.name
                print(f"[{issue.duration:5.2f} {self.type_display[issuetype]}] {issue.key}: {issue.summary}")
                if self.verbose:
                    print(f"           started:   {issue.start_time()}")
                    print(f"           completed: {issue.completed_time()}")
            print()

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


def update_issue_store(all_issues, csv_file):
    new_issues = set()
    old_issues = load_old_issues(csv_file)

    for issue in all_issues:
        if issue.key not in old_issues:
            new_issues.add(issue)

    if new_issues:
        save_new_issues(csv_file, new_issues)


def load_old_issues(csv_file):
    issue_keys = set()
    with open(csv_file, 'r', encoding="UTF8") as f:
        csv_reader = csv.DictReader(f)
        for line in csv_reader:
            issue_keys.add(line["Key"])
    return issue_keys


def save_new_issues(csv_file, new_issues):
    with open(csv_file, 'a', encoding="UTF8") as f:
        field_names = ["Key", "Epic", "Status", "Summary", "Started", "Done", "Duration"]
        csv_writer = csv.DictWriter(f, fieldnames=field_names)
        for issue in new_issues:
            rowdata = {
                "Key":      issue.key,
                "Epic":     issue.epic_key(),
                "Status":   issue.status,
                "Summary":  issue.summary,
                "Started":  issue.start_time(),
                "Done":     issue.completed_time(),
                "Duration": issue.duration
            }
            csv_writer.writerow(rowdata)


def jira_from_date_days_ago(days_ago):
    today = this.date_source.today()
    from_date = today - datetime.timedelta(days=days_ago)
    return str(from_date)


def jira_to_date():
    today = this.date_source.today()
    to_date = today + datetime.timedelta(days=1)
    return str(to_date)


def project_for(labels):
    for label in labels:
        if is_project(label):
            return label.split("_")[0]
    return "Unplanned"


def is_project(label):
    return "Team" not in label
