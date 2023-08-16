import pytest
import dateutil.parser
from ittools.jira.jira_ext import _business_days


@pytest.mark.parametrize(
    "start, end, expected, message",
    [
        (
            "2022-03-01T10:00:00+1100",
            "2022-03-02T10:00:00+1100",
            1.0,
            "Exactly one day",
        ),
        (
            "2022-09-05T09:00:00+1000",
            "2022-09-06T11:30:00+1000",
            1.3125,
            "Minutes are handled",
        ),
        (
            "2022-03-01T10:00:00+1100",
            "2022-03-01T12:00:00+1100",
            0.25,
            "Same day start/end",
        ),
        (
            "2022-03-01T16:00:00+1100",
            "2022-03-02T10:00:00+1100",
            0.25,
            "Skip night hours",
        ),
        (
            "2022-09-06T11:00:00+1000",
            "2022-09-07T10:00:00+1000",
            0.875,
            "Skip night hours",
        ),
        (
            "2022-03-01T10:00:00+1100",
            "2022-03-08T10:00:00+1100",
            5.0,
            "Exactly one week",
        ),
        (
            "2022-09-14T19:00:00+1000",
            "2022-09-15T10:00:00+1000",
            0.125,
            "Start after hours",
        ),
    ],
)
def test_business_days(start, end, expected, message):
    start = dateutil.parser.isoparse(start)
    end = dateutil.parser.isoparse(end)
    assert _business_days(start, end) == expected, message
