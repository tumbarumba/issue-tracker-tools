from ittools.config import load_issue_tracker_config


def test_load_config():
    config = load_issue_tracker_config("example/issuetracker.yml")

    assert config.jira_config.url == "https://url.of.jira/"
    assert len(config.jira_config.statuses) == 10
    assert config.jira_config.statuses[0]["name"] == "Backlog"
    assert len(config.jira_config.issuetypes) == 3
    assert config.jira_config.issuetypes[0]["name"] == "Story"
    assert config.teams["Team1"] == ["John Doe", "James Dean"]
    assert config.teams["Team2"] == ["Jane Doe", "Jessica Rabbit"]
