import textwrap
from unittest.mock import Mock

from ittools.config import ReportOptions
from ittools.cfd.cfd_db import store_project_counts
from ittools.domain.epic import Epic
from ittools.domain.issue_counts import IssueCounts
from ittools.domain.project import Project


def test_csv_created_when_missing(tmp_path):
    options = mock_options(tmp_path)
    project = mock_project("test_project", [mock_epic("DS-1111", IssueCounts(1, 1, 1))])
    csv_path = tmp_path / "epics" / "DS-1111" / "progress.csv"

    store_project_counts("2022-08-16", project, options)

    assert csv_path.exists()
    assert csv_path.read_text() == textwrap.dedent(
        """\
        date,epic,pending,in_progress,done,total
        2022-08-16,DS-1111,1,1,1,3
        """
    )


def test_csv_appended_when_already_present(tmp_path):
    options = mock_options(tmp_path)
    project = mock_project("test_project", [mock_epic("DS-2222", IssueCounts(1, 1, 1))])
    csv_path = tmp_path / "epics" / "DS-2222" / "progress.csv"
    setup_initial_csv(
        csv_path,
        textwrap.dedent(
            """\
        date,epic,pending,in_progress,done,total
        2022-08-15,DS-2222,1,2,0,3
        """
        ),
    )

    store_project_counts("2022-08-16", project, options)

    assert csv_path.read_text() == textwrap.dedent(
        """\
        date,epic,pending,in_progress,done,total
        2022-08-15,DS-2222,1,2,0,3
        2022-08-16,DS-2222,1,1,1,3
        """
    )


def test_csv_fills_in_missing_dates(tmp_path):
    options = mock_options(tmp_path)
    project = mock_project("test_project", [mock_epic("DS-3333", IssueCounts(1, 1, 1))])
    csv_path = tmp_path / "epics" / "DS-3333" / "progress.csv"
    setup_initial_csv(
        csv_path,
        textwrap.dedent(
            """\
        date,project,pending,in_progress,done,total
        2022-08-13,DS-3333,1,2,0,3
        """
        ),
    )

    store_project_counts("2022-08-16", project, options)

    assert csv_path.read_text() == textwrap.dedent(
        """\
        date,epic,pending,in_progress,done,total
        2022-08-13,DS-3333,1,2,0,3
        2022-08-14,DS-3333,1,2,0,3
        2022-08-15,DS-3333,1,2,0,3
        2022-08-16,DS-3333,1,1,1,3
        """
    )


def setup_initial_csv(csv_path, content):
    csv_path.parent.mkdir(parents=True)
    with csv_path.open("w", encoding="UTF8") as f:
        f.write(content)


def mock_epic(key: str, issue_counts: IssueCounts) -> Epic:
    epic = Mock(spec=Epic)
    epic.key = key
    epic.issue_counts = issue_counts
    return epic


def mock_project(key: str, epics: list[Epic]) -> Project:
    project = Mock(spec=Project)
    project.key = key
    project.epics = epics
    # project.issue_counts = issue_counts
    return project


def mock_options(tmp_path) -> ReportOptions:
    options = Mock(spec=ReportOptions)
    options.report_dir = str(tmp_path)
    return options
