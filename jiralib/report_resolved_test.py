import pytest
from datetime import date
from unittest.mock import Mock

from . import report_resolved as rr

DATE_OF_TEST = date(2022, 12, 23)


@pytest.fixture(autouse=True)
def mock_date_source():
    # Setup
    org_date_source = rr.date_source
    rr.date_source = Mock()
    rr.date_source.today = Mock(return_value=DATE_OF_TEST)

    # Run the tests
    yield

    # Teardown
    rr.date_source = org_date_source


def test_from_date_days_ago():
    from_str = rr.jira_from_date_days_ago(7)
    assert from_str == "2022-12-16", f"7 days before {DATE_OF_TEST} should be 2022-12-16"


def test_to_date_blank():
    to_str = rr.jira_to_date()
    assert to_str == "2022-12-24", f"to_date on {DATE_OF_TEST} should be 2022-12-24"

def test_projects_without_labels_are_unplanned():
    assert rr.project_for([]) == "Unplanned"

def test_project_label_excludes_teams():
    assert rr.project_for(["TeamTBD"]) == "Unplanned"
    assert rr.project_for(["TeamTBD", "CBG"]) == "CBG"

def test_project_excludes_milestones():
    assert rr.project_for(["CBG_GTM"]) == "CBG"
