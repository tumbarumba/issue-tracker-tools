from __future__ import annotations

from typing import Any, List

from ittools.domain.epic import Epic
from ittools.domain.project import Project

COLUMN_NAMES = ["Key", "Epic", "Pending", "In Progress", "Done", "Total"]
COLUMN_MARGIN = 2
DEFAULT_COLUMN_WIDTHS = list(
    map(lambda col_name: len(col_name) + COLUMN_MARGIN, COLUMN_NAMES)
)


class ProjectReport:
    def __init__(self: ProjectReport, project: Project):
        self.project = project
        self.col_widths = calculate_column_widths(project.epics)

    def run(self: ProjectReport, report_date: str) -> None:
        print(f"Project: {self.project.key}")
        print(f"Date: {report_date}")
        print()

        row_separator = sum(self.col_widths) * "="
        print(self.format_row(COLUMN_NAMES))
        print(row_separator)
        for epic in self.project.epics:
            print(self.format_row(epic_row_values(epic)))
        print(row_separator)
        print(self.format_row(total_row_values(self.project)))
        print()

    def format_row(self: ProjectReport, values: List[Any]) -> str:
        return (
            f"{values[0]:<{self.col_widths[0]}}"  # Key
            f"{values[1]:<{self.col_widths[1]}}"  # Summary
            f"{values[2]:>{self.col_widths[2]}}"  # Pending
            f"{values[3]:>{self.col_widths[3]}}"  # In Progress
            f"{values[4]:>{self.col_widths[4]}}"  # Done
            f"{values[5]:>{self.col_widths[5]}}"  # Total
        )


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


def total_row_values(project: Project) -> List[Any]:
    return [
        "",
        "",
        project.issue_counts.pending,
        project.issue_counts.in_progress,
        project.issue_counts.done,
        project.issue_counts.total,
    ]
