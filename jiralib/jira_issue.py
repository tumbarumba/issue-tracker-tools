import dateutil.parser
import numpy as np
import re
import jiralib.jira_builder as jb
import pytz
from datetime import datetime


class StateCounts:
    def __init__(self, pending, in_progress, done):
        self.pending = pending
        self.in_progress = in_progress
        self.done = done
        self.total = pending + in_progress + done

    @classmethod
    def zero(cls):
        return cls(0, 0, 0)

    def __add__(self, other):
        return StateCounts(self.pending + other.pending,
                           self.in_progress + other.in_progress,
                           self.done + other.done)

    def __eq__(self, other):
        return (self.pending == other.pending
                and self.in_progress == other.in_progress
                and self.done == other.done)

    def __str__(self):
        return f"StateCounts({self.pending},{self.in_progress},{self.done})"


class JiraIssue:
    def __init__(self, jira_issue):
        self.jira_issue = jira_issue
        self.key = jira_issue.key
        self.summary = jira_issue.fields.summary
        self.status = jira_issue.fields.status.name
        duration_end = self.completed_time() or datetime.now()
        self.duration = business_days(self.start_time(), duration_end)
        self.calendar_duration = calendar_days(self.start_time(), duration_end)

    def start_time(self):
        return self.in_progress_time() or self.created_time()

    def created_time(self):
        return dateutil.parser.isoparse(self.jira_issue.fields.created)

    def in_progress_time(self):
        for history in self.jira_issue.changelog.histories:
            for item in history.items:
                if item.field == "status":
                    if item.toString == "In Progress":
                        return dateutil.parser.isoparse(history.created)
        return None

    def completed_time(self):
        return self.done_time() or self.resolution_time()

    def resolution_time(self):
        if self.jira_issue.fields.resolutiondate:
            return dateutil.parser.isoparse(self.jira_issue.fields.resolutiondate)
        return None

    def done_time(self):
        result = None
        for history in self.jira_issue.changelog.histories:
            for item in history.items:
                if item.field == "status":
                    if item.toString in ["Awaiting Demo", "Done"]:
                        return dateutil.parser.isoparse(history.created)
        return result

    def fix_versions(self):
        versions = []
        if "fixVersions" in self.jira_issue.raw["fields"]:
            versions = self.jira_issue.raw["fields"]["fixVersions"]
        return list(map(lambda version: version["name"], versions))

    def epic_key(self):
        return self.jira_issue.raw["fields"][jb._EPIC_LINK_FIELD_]

    def epic_status(self):
        return self.jira_issue.raw["fields"][jb._EPIC_STATUS_FIELD_]["value"]

    def epic_summary(self):
        return self.jira_issue.raw["fields"][jb._EPIC_STATUS_FIELD_]["summary"]


class JiraEpic(JiraIssue):
    @classmethod
    def create(cls, jira_issue, jira):
        counts = load_epic_counts(jira_issue, jira)
        return cls(jira_issue, counts)

    def __init__(self, jira_issue, state_counts):
        super().__init__(jira_issue)
        self.state_counts = state_counts


story_estimate_pattern = re.compile(r"^Expected size: (\d+)")
in_progress_states = ["In Progress", "In Review", "Awaiting Merge", "Under Test"]
done_states = ["Awaiting Demo", "Done"]
exclude_story_states = ["Closed", "Duplicate"]


def load_epic_counts(epic, jira):
    estimated_count = load_epic_estimated_stories(epic, jira)
    all_stories = jb.JiraQueries(jira).get_epic_stories(epic.key)
    if len(all_stories) == 0:
        return StateCounts(estimated_count, 0, 0)

    stories = list(filter(lambda story: story.fields.status.name not in exclude_story_states, all_stories))

    actual_total_count = len(stories)
    reported_total_count = max(estimated_count, actual_total_count)

    done_count = len(filter_by_state(stories, done_states))
    in_progress_count = len(filter_by_state(stories, in_progress_states))
    pending_count = reported_total_count - in_progress_count - done_count
    if epic.raw["fields"][jb._EPIC_STATUS_FIELD_]["value"] == "Done":
        pending_count = 0
    return StateCounts(pending_count, in_progress_count, done_count)


def load_epic_estimated_stories(epic, jira):
    estimated_stories = 10
    for comment in jira.comments(epic):
        match = story_estimate_pattern.match(comment.body)
        if match:
            estimated_stories = int(match.group(1))

    return estimated_stories


def filter_by_state(stories, states_to_check):
    return list(filter(lambda story: story.fields.status.name in states_to_check, stories))


BUSINESS_HOURS_START = 9
BUSINESS_HOURS_END = 17


def business_days(start_time, end_time):
    if not (start_time and end_time):
        return None
    bus_days = np.busday_count(start_time.date(), end_time.date())
    bus_hours = hours_in_working_day(start_time, end_time)
    return bus_days + (bus_hours / 8)


def hours_in_working_day(start_time, end_time):
    bus_hours = end_hours(end_time) - start_hours(start_time)
    if bus_hours < -8:
        bus_hours = (bus_hours + 24) * -1
    if bus_hours > 8:
        bus_hours = 8
    return bus_hours


def start_hours(start_time):
    start_hours = start_time.hour + start_time.minute / 60
    return min(start_hours, BUSINESS_HOURS_END)


def end_hours(end_time):
    end_hours = end_time.hour + end_time.minute / 60
    return max(end_hours, BUSINESS_HOURS_START)


def calendar_days(start_time, end_time):
    if not (start_time and end_time):
        return None
    return (end_time.astimezone(pytz.UTC) - start_time.astimezone(pytz.UTC)).total_seconds() / 60 / 60 / 24
