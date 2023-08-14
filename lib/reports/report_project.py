from __future__ import annotations

import csv
from datetime import date
from functools import reduce
from pathlib import Path
from typing import Any, Dict, List

from dateutil.parser import isoparse
from dateutil.relativedelta import relativedelta

from lib.issues.issue import Epic
from lib.issues.issue_counts import IssueCounts
from lib.issues.issue_provider import IssueProvider

COLUMN_NAMES = ["Key", "Epic", "Pending", "In Progress", "Done", "Total"]
COLUMN_MARGIN = 2
DEFAULT_COLUMN_WIDTHS = list(
    map(lambda col_name: len(col_name) + COLUMN_MARGIN, COLUMN_NAMES)
)


class ProjectReport:
    def __init__(self: ProjectReport, issue_provider: IssueProvider, verbose: bool):
        self.issue_provider = issue_provider
        self.verbose: bool = verbose

    def run(self: ProjectReport, project_key: str, csv_file: str) -> None:
        today = str(date.today())

        print(f"Project: {project_key}")
        print(f"Date: {today}")
        print()

        epics = self.issue_provider.load_project_epics(project_key)

        col_widths = calculate_column_widths(epics)

        table_header = format_row(col_widths, COLUMN_NAMES)
        row_separator = len(table_header) * "="

        print(table_header)
        print(row_separator)
        for epic in epics:
            print(format_row(col_widths, epic_row_values(epic)))

        project_counts = accumulate_counts_for(epics)

        print(row_separator)
        print(format_row(col_widths, total_row_values(project_counts)))
        print()

        store_project_counts(today, project_key, project_counts, csv_file)


def calculate_column_widths(epics) -> List[int]:
    col_widths = DEFAULT_COLUMN_WIDTHS.copy()
    col_widths[0] = max(len(epic.key) for epic in epics) + COLUMN_MARGIN
    col_widths[1] = max(len(epic.summary) for epic in epics)
    return col_widths


def epic_row_values(epic: Epic) -> List[Any]:
    return [
        epic.key,
        epic.summary,
        epic.issue_counts.pending,
        epic.issue_counts.in_progress,
        epic.issue_counts.done,
        epic.issue_counts.total,
    ]


def total_row_values(total_counts: IssueCounts) -> List[Any]:
    return [
        "",
        "",
        total_counts.pending,
        total_counts.in_progress,
        total_counts.done,
        total_counts.total,
    ]


def format_row(col_widths: List[int], cell_values: List[Any]) -> str:
    return (
        f"{cell_values[0]:<{col_widths[0]}}"  # Key
        f"{cell_values[1]:<{col_widths[1]}}"  # Summary
        f"{cell_values[2]:>{col_widths[2]}}"  # Pending
        f"{cell_values[3]:>{col_widths[3]}}"  # In Progress
        f"{cell_values[4]:>{col_widths[4]}}"  # Done
        f"{cell_values[5]:>{col_widths[5]}}"  # Total
    )


def accumulate_counts_for(epics) -> IssueCounts:
    return reduce(
        lambda accumulation, epic: accumulation + epic.issue_counts,
        epics,
        IssueCounts.zero(),
    )


def store_project_counts(
    count_date: str, project_key: str, project_counts: IssueCounts, csv_file: str
) -> None:
    csv_path = Path(csv_file)

    if not csv_path.parent.exists():
        print(f"Making directory {str(csv_path.parent)}")
        csv_path.parent.mkdir(parents=True, exist_ok=True)

    csv_data = read_csv_data(csv_path)
    add_missing_dates(csv_data, count_date)
    csv_data[count_date] = project_counts
    write_csv_data(csv_path, project_key, csv_data)


def read_csv_data(csv_path: Path) -> Dict[str, IssueCounts]:
    csv_data = dict()

    if csv_path.exists():
        with csv_path.open("r", encoding="UTF8") as f:
            csv_reader = csv.DictReader(f)
            for row in csv_reader:
                csv_data[row["date"]] = counts_from_row(row)

    return csv_data


def counts_from_row(row: Dict[str, str]) -> IssueCounts:
    pending = int(row["pending"])
    in_progress = int(row["in_progress"])
    done = int(row["done"])
    return IssueCounts(pending, in_progress, done)


def write_csv_data(
    csv_path: Path, project_key: str, csv_data: Dict[str, IssueCounts]
) -> None:
    with csv_path.open("w", encoding="UTF8") as f:
        field_names = ["date", "project", "pending", "in_progress", "done", "total"]
        csv_writer = csv.DictWriter(f, fieldnames=field_names)
        csv_writer.writeheader()
        for key in sorted(csv_data.keys()):
            counts = csv_data[key]
            csv_writer.writerow(
                {
                    "date": key,
                    "project": project_key,
                    "pending": counts.pending,
                    "in_progress": counts.in_progress,
                    "done": counts.done,
                    "total": counts.total,
                }
            )


def add_missing_dates(csv_data: Dict[str, IssueCounts], date_to_add_str: str) -> None:
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
