from itertools import groupby

from .jira_issue import JiraIssue


class WorkingReport:
    def __init__(self, opts, query):
        self.verbose = opts.verbose
        self.query = query
        self.type_display = {
            issuetype["name"]: issuetype["display"] for index, issuetype in enumerate(opts.jira_config.issuetypes)
        }

    def run(self, group):
        report_issues = list(map(JiraIssue, self.query.get_working_issues()))
        print(f"Working issue count: {len(report_issues)}\n")

        if group:
            self.report_issues_grouped_by_epic(report_issues)
        else:
            self.report_issues(report_issues)

    def report_issues(self, issues):
        for issue in sorted(issues, key=lambda issue: issue.duration):
            self.print_issue(issue)

    def report_issues_grouped_by_epic(self, issues):
        epics = self.epics_for(issues)
        sorted_issues = sorted(issues, key=lambda i: self.rank_for(i.epic_key(), epics))
        for epic_key, epic_issues in groupby(sorted_issues, lambda issue: issue.epic_key() or ""):
            if epic_key:
                epic = epics[epic_key]
                print(f"{epic.key}: {epic.summary}")
            else:
                print("No Epic:")
            for issue in epic_issues:
                self.print_issue(issue)
            print()

    def epics_for(self, issues):
        epics = {}
        for issue in issues:
            if issue.epic_key() and not issue.epic_key() in epics:
                epic = JiraIssue(self.query.get_single_issue(issue.epic_key()))
                epics[epic.key] = epic

        return epics

    def rank_for(self, epic_key, epics):
        if epic_key in epics:
            return epics[epic_key].rank()
        else:
            return "Ω"  # Omega should sort last alphabetically

    def print_issue(self, issue):
        typeicon = self.type_display[issue.jira_issue.fields.issuetype.name]
        assignee = issue.jira_issue.fields.assignee
        print(f"{issue.duration:5.2f} {typeicon} {issue.key}: {issue.summary} ({assignee})")
