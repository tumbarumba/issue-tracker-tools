import csv
from pathlib import Path
from typing import Dict

from dateutil.parser import isoparse
from dateutil.relativedelta import relativedelta

from lib.config import ReportOptions
from lib.domain.issue_counts import IssueCounts
from lib.domain.project import Project

PROJECT_PROGRESS_CSV = "progress.csv"


def store_project_counts(
    count_date: str, project: Project, options: ReportOptions
) -> None:
    progress_csv_path = get_progress_csv_path(options)
    csv_data = read_csv_data(progress_csv_path)
    add_missing_dates(csv_data, count_date)
    csv_data[count_date] = project.issue_counts
    write_csv_data(progress_csv_path, project.key, csv_data)


def get_progress_csv_path(options):
    report_path = Path(options.report_dir)
    project_report_path = report_path / options.project_config.project_label
    if not project_report_path.exists():
        print(f"Making directory {str(project_report_path)}")
        project_report_path.mkdir(parents=True, exist_ok=True)
    return project_report_path / PROJECT_PROGRESS_CSV


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
