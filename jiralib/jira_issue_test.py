import pytest
import dateutil.parser
from .jira_issue import business_days


@pytest.mark.parametrize("start, end, expected, message", [
    ("2022-03-01T10:00:00+1100", "2022-03-02T10:00:00+1100", 1.0, "Exactly one day"),
    ("2022-03-01T10:01:00+1100", "2022-03-02T10:59:00+1100", 1.0, "Minutes are ignored"),
    ("2022-03-01T10:00:00+1100", "2022-03-01T12:00:00+1100", 0.25, "Same day start/end"),
    ("2022-03-01T16:00:00+1100", "2022-03-02T10:00:00+1100", 0.25, "Skip night hours"),
    ("2022-03-01T10:00:00+1100", "2022-03-08T10:00:00+1100", 5.0, "Exactly one week")
])
def test_business_days(start, end, expected, message):
    start = dateutil.parser.isoparse(start)
    end = dateutil.parser.isoparse(end)
    assert business_days(start, end) == expected, message
