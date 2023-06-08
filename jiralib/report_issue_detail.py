from __future__ import annotations
from typing import List
from dateutil.tz import tzlocal
import re
import json
import jsonpickle

from .jira_ext import JiraServer, JiraIssue


class IssueDetailReport:
    def __init__(self: IssueDetailReport, jira: JiraServer, verbose: bool):
        self.jira = jira
        self.verbose: bool = verbose

    def run(self: IssueDetailReport, issue_keys: List[str]) -> None:
        try:
            for issue in self.jira.query_issue_keys(issue_keys):
                self.report_issue_detail(issue)
                print("")
        except Exception as e:
            print(f"Failed: {e}")

    def report_issue_detail(self: IssueDetailReport, issue: JiraIssue):  # noqa: C901
        if self.verbose:
            print(" json dump:")
            serialised = jsonpickle.encode(issue.raw_issue)
            print(json.dumps(json.loads(serialised), indent=2))

        is_epic = issue.issue_type == "Epic"

        print(f"{issue.key}: {issue.summary}")
        print(f" type:       {issue.issue_type}")
        print(f" status:     {issue.status}")
        if is_epic:
            print(f" epic status:{issue.epic_status}")
        if "parent" in issue.raw_issue.raw["fields"]:
            parent = issue.raw_issue.fields.parent
            print(f" parent:     {parent.key} - {parent.fields.summary}")
        if issue.epic_key:
            epic = self.jira.issue(issue.epic_key)
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

        creator_initials = initials_for(issue.raw_issue.fields.creator.displayName)
        print(f" history:    {issue.raw_issue.fields.created} [{creator_initials}]: Created")
        for history in issue.raw_issue.changelog.histories:
            for item in history.items:
                if item.field == "status":
                    initials = initials_for(history.author.displayName)
                    print(f"             {history.created} [{initials}]: {item.fromString} => {item.toString}")

        comments = self.jira.comments(issue.key)
        if comments:
            print(" comments:")
            for comment in comments:
                print(formatted_comment(comment))

        if issue.raw_issue.fields.subtasks:
            print(" subtasks:")
            for subtask in issue.raw_issue.fields.subtasks:
                print(f"             {subtask.key}: {subtask.fields.summary}")

            for subtask in issue.raw_issue.fields.subtasks:
                print("\n===\n")
                self.report_issue_detail(subtask.key)

        if is_epic:
            print(" stories:")
            stories = self.jira.search_issues(f"'Epic Link' = {issue.key} order by key")
            for story in stories:
                print(f"             {story.key}: {story.fields.summary}")


def initials_for(full_name: str) -> str:
    return "".join(name[0].upper() for name in full_name.split())


def formatted_comment(comment: str) -> str:
    if comment.author.name == "gitlab-jira":
        git_comment_pattern = re.compile(r"^\[([\w ]+)\|.+\{quote\}(.*)\{quote\}$")
        match = git_comment_pattern.match(comment.body)
        if match:
            return f"             {comment.created} [git: {initials_for(match.group(1))}]: {match.group(2)}"

    return f"             {comment.created} [{initials_for(comment.author.displayName)}]: {comment.body}"
