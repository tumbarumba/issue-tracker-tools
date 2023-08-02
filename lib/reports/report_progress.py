from __future__ import annotations
from typing import List, Tuple
from datetime import date
from dateutil.parser import isoparse
from dateutil.relativedelta import relativedelta
from pathlib import Path
import csv

from lib.jira.jira_ext import JiraServer, JiraEpic
from lib.issues.issue_counts import IssueCounts


class ProgressReport:
    def __init__(self: ProgressReport, jira: JiraServer, verbose: bool):
        self.jira: JiraServer = jira
        self.verbose: bool = verbose

    def run(self: ProgressReport, label: str, csv_file: str) -> None:
        self.report_cumulative_flow(label, csv_file)

    def report_cumulative_flow(self: ProgressReport, label: str, csv_file: str) -> None:
        today = str(date.today())
        print(f"Label: {label}\nDate: {today}")
        epics: List[JiraEpic] = self.jira.query_project_epics(label)
        keys: List[str] = [epic.key for epic in epics]
        summaries: List[str] = [epic.summary for epic in epics]

        key_space, summary_space = self.table_spacing_calculation(keys, summaries)
        table_length = self.print_header(key_space, summary_space)
        project_counts = self.print_body(epics, keys, key_space, summaries, summary_space, table_length)

        store_project_counts(today, label, project_counts, csv_file)

    def print_header(self: ProgressReport, key_space: int, summary_space: int) -> int:
        table_header = f"Key{(key_space-3)*' '}Epic{(summary_space-4)*' '}Pending  In Progress  Done  Total"
        print(f"\n{table_header}\n{(len(table_header))*'='}")
        return len(table_header)

    def print_body(self: ProgressReport,
                   epics: List[JiraEpic],
                   keys: List[str],
                   key_space: int,
                   summaries: List[str],
                   summary_space: int,
                   table_length: int) -> int:
        project_counts = IssueCounts.zero()
        i = 0
        for epic in epics:
            project_counts += epic.issue_counts
            key_epic_display = f"{keys[i]}{(key_space-len(keys[i]))*' '}{summaries[i]}{(summary_space-len(summaries[i]))*' '}"
            stats_display = self.format_stats_str(epic.issue_counts)
            print(f"{key_epic_display}{stats_display}")
            i += 1

        print(f"{table_length*'='}\n{(key_space+summary_space)*' '}{self.format_stats_str(project_counts)}\n")
        return project_counts

    def table_spacing_calculation(self: ProgressReport, keys: List[str], summaries: List[str]) -> Tuple[int, int]:
        space_key = 0
        space_summary = 0
        for i in range(len(keys)):
            if len(keys[i]) > space_key:
                space_key = len(keys[i])
            if len(summaries[i]) > space_summary:
                space_summary = len(summaries[i])
        return (space_key+2, space_summary+2)

    def format_stats_str(self: ProgressReport, stats: IssueCounts) -> str:
        spacing = [7, 13, 6, 7]
        stats_display = ""
        # print("stats:  ", stats)
        data = self.get_project_stats(stats)
        for i in range(len(spacing)):
            stats_display += f"{self.build_stat(spacing[i], data[i])}"

        return (str(stats_display))

    def get_project_stats(self: ProgressReport, project_stats: IssueCounts) -> List[int]:
        stat_types = ["pending", "in_progress", "done", "total"]
        formated_project_stats: List[int] = []
        for i in range(len(stat_types)):
            type = getattr(project_stats, stat_types[i])
            formated_project_stats.append(type)
        return (formated_project_stats)

    def build_stat(self: ProgressReport, base_spacing: int, data: int) -> str:
        spacer = base_spacing-len(str(data))
        stat_display = f"{spacer*' '}{data}"
        return (stat_display)


def store_project_counts(count_date, project, project_counts, csv_file):
    csv_path = Path(csv_file)

    if not csv_path.parent.exists():
        print(f"Making directory {str(csv_path.parent)}")
        csv_path.parent.mkdir(parents=True, exist_ok=True)

    csv_data = read_csv_data(csv_path)
    add_missing_dates(csv_data, count_date)
    csv_data[count_date] = project_counts
    write_csv_data(csv_path, project, csv_data)


def read_csv_data(csv_path):
    csv_data = dict()

    if csv_path.exists():
        with csv_path.open('r', encoding="UTF8") as f:
            csv_reader = csv.DictReader(f)
            for row in csv_reader:
                csv_data[row["date"]] = counts_from_row(row)

    return csv_data


def counts_from_row(row):
    pending = int(row["pending"])
    in_progress = int(row["in_progress"])
    done = int(row["done"])
    return IssueCounts(pending, in_progress, done)


def write_csv_data(csv_path, project, csv_data):
    with csv_path.open('w', encoding="UTF8") as f:
        field_names = ["date", "project", "pending", "in_progress", "done", "total"]
        csv_writer = csv.DictWriter(f, fieldnames=field_names)
        csv_writer.writeheader()
        for key in sorted(csv_data.keys()):
            counts = csv_data[key]
            csv_writer.writerow({
                "date":         key,
                "project":      project,
                "pending":      counts.pending,
                "in_progress":  counts.in_progress,
                "done":         counts.done,
                "total":        counts.total
            })


def add_missing_dates(csv_data, date_to_add_str):
    if not csv_data:
        return

    date_to_add = isoparse(date_to_add_str).date()

    keys = sorted(csv_data.keys())
    last_date = isoparse(keys[-1]).date()
    while True:
        next_date = last_date + relativedelta(days=+1)
        if next_date >= date_to_add:
            # No date missing
            return
        csv_data[str(next_date)] = csv_data[str(last_date)]
        last_date = next_date
