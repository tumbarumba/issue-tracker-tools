from dateutil.tz import tzlocal
import re
import json
import jsonpickle
import webbrowser

from .jira_issue import JiraIssue


class IssueDetailReport:
    def __init__(self, opts, jira):
        self.verbose = opts.verbose
        self.jira_base_url = opts.jira_config.url
        self.jira = jira

    def run(self, issue_key, open):
        self.report_issue_detail(issue_key)
        if open:
            url = f"{self.jira_base_url}/browse/{issue_key}"
            webbrowser.open(url)

    def report_issue_detail(self, issue_key):  # noqa: C901
        issue = JiraIssue(self.jira.issue(issue_key, expand="changelog"))
        is_epic = issue.jira_issue.fields.issuetype.name == "Epic"

        print(f"{issue.key}: {issue.summary}")
        print(f" type:       {issue.jira_issue.fields.issuetype.name}")
        print(f" status:     {issue.status}")
        if is_epic:
            print(f" epic status:{issue.epic_status()}")
        if "parent" in issue.jira_issue.raw["fields"]:
            parent = issue.jira_issue.fields.parent
            print(f" parent:     {parent.key} - {parent.fields.summary}")
        if issue.epic_key():
            epic = self.jira.issue(issue.epic_key())
            print(f" epic:       {epic.key}: {epic.fields.summary}")
        if issue.fix_versions():
            print(f" fixed:      {', '.join(issue.fix_versions())}")
        if issue.start_time():
            print(f" started:    {issue.start_time().astimezone(tzlocal())}")
        else:
            print(" started:    n/a")
        if issue.completed_time():
            print(f" completed:  {issue.completed_time().astimezone(tzlocal())}")
        else:
            print(" completed:  n/a")
        if issue.start_time():
            print(f" duration:   {issue.duration:.2f} business days ({issue.calendar_duration:.2f} calendar days)")
        else:
            print(" duration:   n/a")

        creator_initials = initials_for(issue.jira_issue.fields.creator.displayName)
        print(f" history:    {issue.jira_issue.fields.created} [{creator_initials}]: Created")
        for history in issue.jira_issue.changelog.histories:
            for item in history.items:
                if item.field == "status":
                    initials = initials_for(history.author.displayName)
                    print(f"             {history.created} [{initials}]: {item.fromString} => {item.toString}")

        print(" comments:")
        for comment in issue.jira_issue.fields.comment.comments:
            print(formatted_comment(comment))

        if issue.jira_issue.fields.subtasks:
            print(" subtasks:")
            for subtask in issue.jira_issue.fields.subtasks:
                print(f"             {subtask.key}: {subtask.fields.summary}")

            for subtask in issue.jira_issue.fields.subtasks:
                print("\n===\n")
                self.report_issue_detail(subtask.key)

        if is_epic:
            print(" stories:")
            stories = self.jira.search_issues(f"'Epic Link' = {issue.key} order by key")
            for story in stories:
                print(f"             {story.key}: {story.fields.summary}")

        if self.verbose:
            print(" json dump:")
            serialised = jsonpickle.encode(issue.jira_issue)
            print(json.dumps(json.loads(serialised), indent=2))


def initials_for(full_name):
    return "".join(name[0].upper() for name in full_name.split())


git_comment_pattern = re.compile(r"^\[([\w ]+)\|.+\{quote\}(.*)\{quote\}$")


def formatted_comment(comment):
    if comment.author.name == "gitlab-jira":
        match = git_comment_pattern.match(comment.body)
        if match:
            return f"             {comment.created} [git: {initials_for(match.group(1))}]: {match.group(2)}"

    return f"             {comment.created} [{initials_for(comment.author.displayName)}]: {comment.body}"
