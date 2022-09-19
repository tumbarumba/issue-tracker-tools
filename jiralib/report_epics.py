from .jira_issue import JiraIssue
import sys
import jira
import re


class EpicReport:
    def __init__(self, opts, query):
        self.verbose = opts.verbose
        statuses = opts.jira_config.statuses
        self.status_order = {status["name"]: index for index, status in enumerate(statuses)}
        self.status_display = {status["name"]: status["display"] for index, status in enumerate(statuses)}
        self.project_label = opts.project_config.project_label
        self.query = query

    def run(self, subject):
        epics = self.find_epics(subject)
        self.print_epics_and_stories(epics)

    def find_epics(self, subject):
        try:
            if re.match("[A-Z]{2}-[0-9]{4}", subject):
                # if a specific epic is provided
                return list(self.query.get_single_issue(subject))
            elif subject:
                # if project specified
                return self.query.get_project_epics(self.project_label)
            else:
                return self.query.get_all_open_epics()
        except jira.JIRAError:
            sys.exit("Epic does not exist or is not formatted correctly, eg. DS-1000.")

    def print_epics_and_stories(self, epics):
        for epic in epics:
            print("{}: {}".format(epic.key, epic.fields.summary))
            stories = self.query.get_epic_stories(epic.key)
            for story in sorted(stories, key=lambda s: self.sort_by_status_then_key(s)):
                issue = JiraIssue(story)
                print("\t[{}] {}: {}".format(self.status_display[issue.status], issue.key, issue.summary))
                if issue.duration:
                    print(f"\t\tworking duration: {issue.duration:.2f} days")

    def sort_by_status_then_key(self, story):
        return (self.status_order[story.fields.status.name], story.key)
