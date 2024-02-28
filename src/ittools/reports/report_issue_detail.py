from __future__ import annotations
from typing import Dict, List
from dateutil.tz import tzlocal
import re
import json
import jsonpickle

from ittools.config import JiraConfig
from ittools.jira.jira_ext import JiraServer, JiraIssue


class IssueDetailReport:
    def __init__(self, jira_config: JiraConfig, jira: JiraServer, verbose: bool, summary: bool):
        self.jira = jira
        self.verbose = verbose
        self.summary = summary
        self.type_display: Dict[str, str] = {
            issue_type["name"]: issue_type["display"]
            for index, issue_type in enumerate(jira_config.issuetypes)
        }

    def run(self, issue_keys: List[str]) -> None:
        try:
            for issue in self.jira.query_issue_keys(issue_keys):
                self.report_issue(issue)
        except Exception as e:
            print(f"Failed: {e}")

    def report_issue(self, issue: JiraIssue) -> None:
        if self.verbose:
            print(" json dump:")
            serialised = jsonpickle.encode(issue.raw_issue)
            print(json.dumps(json.loads(serialised), indent=2))

        if self.summary:
            self.report_issue_summary(issue)
        else:
            self.report_issue_detail(issue)

    def report_issue_summary(self, issue: JiraIssue) -> None:
        issue_icon = self.type_display[issue.issue_type]
        print(f"{issue_icon} {issue.key}: {issue.summary}")

    def report_issue_detail(self, issue: JiraIssue) -> None:  # noqa: C901
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
            print(
                f" duration:   {issue.duration:.2f} business days ({issue.calendar_duration:.2f} calendar days)"
            )
        else:
            print(" duration:   n/a")

        creator_initials = initials_for(issue.raw_issue.fields.creator.displayName)
        print(
            f" history:    {issue.raw_issue.fields.created} [{creator_initials}]: Created"
        )
        for history in issue.raw_issue.changelog.histories:
            for item in history.items:
                if item.field == "status":
                    initials = initials_for(history.author.displayName)
                    print(
                        f"             {history.created} [{initials}]: {item.fromString} => {item.toString}"
                    )

        print(" state times (business days):")
        print(f"             Selected for Development: {issue.time_in_state('Selected for Development'):7.2f}")
        print(f"             Ready for Development:    {issue.time_in_state('Ready for Development'):7.2f}")

        in_progress_time = issue.time_in_state("In Progress")
        in_review_time = issue.time_in_state("In Review")
        under_test_time = issue.time_in_state("Under Test")
        eng_cycle_time = in_progress_time + in_review_time + under_test_time

        print("             -------------------------------------")
        print(f"               In Progress:            {in_progress_time:7.2f}")
        print(f"               In Review:              {in_review_time:7.2f}")
        print(f"               Under Test:             {under_test_time:7.2f}")
        print("             -------------------------------------")
        print(f"             Engineering:              {eng_cycle_time:7.2f}")

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
                self.report_issue(subtask.key)

        if is_epic:
            print(" stories:")
            stories = self.jira.search_issues(f"'Epic Link' = {issue.key} order by key")
            for story in stories:
                print(f"             {story.key}: {story.fields.summary}")

        print("")


def initials_for(full_name: str) -> str:
    return "".join(name[0].upper() for name in full_name.split())


def formatted_comment(comment: str) -> str:
    if comment.author.name == "gitlab-jira":
        git_comment_pattern = re.compile(r"^\[([\w ]+)\|.+\{quote\}(.*)\{quote\}$")
        match = git_comment_pattern.match(comment.body)
        if match:
            return f"             {comment.created} [git: {initials_for(match.group(1))}]: {match.group(2)}"

    return f"             {comment.created} [{initials_for(comment.author.displayName)}]: {comment.body}"
