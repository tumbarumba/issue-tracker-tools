import textwrap
from unittest.mock import Mock

from ittools.config import ReportOptions
from ittools.cfd.cfd_db import store_project_counts
from ittools.domain.issue_counts import IssueCounts
from ittools.domain.project import Project


def test_csv_created_when_missing(tmp_path):
    options = mock_options(tmp_path)
    project = mock_project("test_project", IssueCounts(1, 1, 1))
    csv_path = tmp_path / "test_project" / "progress.csv"

    store_project_counts("2022-08-16", project, options)

    assert csv_path.exists()
    assert csv_path.read_text() == textwrap.dedent(
        """\
        date,project,pending,in_progress,done,total
        2022-08-16,test_project,1,1,1,3
        """
    )


def test_csv_appended_when_already_present(tmp_path):
    options = mock_options(tmp_path)
    project = mock_project("test_project", IssueCounts(1, 1, 1))
    csv_path = tmp_path / "test_project" / "progress.csv"
    setup_initial_csv(
        csv_path,
        textwrap.dedent(
            """\
        date,project,pending,in_progress,done,total
        2022-08-15,test_project,1,2,0,3
        """
        ),
    )

    store_project_counts("2022-08-16", project, options)

    assert csv_path.read_text() == textwrap.dedent(
        """\
        date,project,pending,in_progress,done,total
        2022-08-15,test_project,1,2,0,3
        2022-08-16,test_project,1,1,1,3
        """
    )


def test_csv_fills_in_missing_dates(tmp_path):
    options = mock_options(tmp_path)
    project = mock_project("test_project", IssueCounts(1, 1, 1))
    csv_path = tmp_path / "test_project" / "progress.csv"
    setup_initial_csv(
        csv_path,
        textwrap.dedent(
            """\
        date,project,pending,in_progress,done,total
        2022-08-13,test_project,1,2,0,3
        """
        ),
    )

    store_project_counts("2022-08-16", project, options)

    assert csv_path.read_text() == textwrap.dedent(
        """\
        date,project,pending,in_progress,done,total
        2022-08-13,test_project,1,2,0,3
        2022-08-14,test_project,1,2,0,3
        2022-08-15,test_project,1,2,0,3
        2022-08-16,test_project,1,1,1,3
        """
    )


def setup_initial_csv(csv_path, content):
    csv_path.parent.mkdir(parents=True)
    with csv_path.open("w", encoding="UTF8") as f:
        f.write(content)


def mock_project(key: str, issue_counts: IssueCounts) -> Project:
    project = Mock(spec=Project)
    project.key = key
    project.issue_counts = issue_counts
    return project


def mock_options(tmp_path) -> ReportOptions:
    options = Mock(spec=ReportOptions)
    options.report_dir = str(tmp_path)
    return options
