from ittools.domain.issue_counts import IssueCounts


def test_can_add_issue_counts():
    assert IssueCounts(1, 1, 1) + IssueCounts(1, 2, 3) == IssueCounts(2, 3, 4)
