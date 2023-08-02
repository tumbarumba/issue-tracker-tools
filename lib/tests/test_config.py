from lib.config import load_yaml, JiraConfig, ProjectConfig


def test_load_jira_config():
    config = load_jira_config_for_test()
    assert config.url == "https://url.of.jira/"
    assert len(config.statuses) == 11
    assert config.statuses[0]["name"] == "Backlog"
    assert len(config.issuetypes) == 3
    assert config.issuetypes[0]["name"] == "Story"


def test_load_project_config():
    config = load_project_config_for_test()
    assert config.project_name == "Project Name"


def load_jira_config_for_test():
    yaml_jira_config = load_yaml("example/jiraconfig.yml", "jira")
    return JiraConfig(yaml_jira_config)


def load_project_config_for_test():
    yaml_project_config = load_yaml("example/projectconfig.yml", "project")
    return ProjectConfig(yaml_project_config)
