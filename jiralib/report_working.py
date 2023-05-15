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
            sorted_issues = sorted(report_issues, key=lambda i: i.epic_key() or "")
            for epic_key, epic_issues in groupby(sorted_issues, lambda issue: issue.epic_key() or ""):
                if epic_key:
                    epic = self.query.get_single_issue(epic_key)
                    print(f"{epic.key}: {epic.fields.summary}")
                else:
                    print("No Epic:")
                for issue in epic_issues:
                    self.print_issue(issue)
                print()
        else:
            for issue in sorted(report_issues, key=lambda issue: issue.duration):
                self.print_issue(issue)

    def print_issue(self, issue):
        typeicon = self.type_display[issue.jira_issue.fields.issuetype.name]
        assignee = issue.jira_issue.fields.assignee
        print(f"{issue.duration:5.2f} {typeicon} {issue.key}: {issue.summary} ({assignee})")
