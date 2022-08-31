import yaml


DEFAULT_STATUSES = [
    {"display": "🔵", "name": "Backlog"},
    {"display": "🌑", "name": "Selected for Development"},
    {"display": "🌘", "name": "Ready for Development"},
    {"display": "🌗", "name": "In Progress"},
    {"display": "🌖", "name": "In Review"},
    {"display": "🌕", "name": "Awaiting Merge"},
    {"display": "🔆", "name": "Awaiting Demo"},
    {"display": "✅", "name": "Done"},
    {"display": "C", "name": "Closed"},
    {"display": "D", "name": "Duplicate"}
]

DEFAULT_ISSUE_TYPES = [
    {"display": "📖", "name": "Story"},
    {"display": "🐞", "name": "Bug"},
    {"display": "🔧", "name": "Task"}
]

class JiraConfig:
    def __init__(self, jira_config):
        self.url = jira_config['url']
        self.statuses = jira_config.get("statuses", DEFAULT_STATUSES)
        self.issuetypes = jira_config.get("issuetypes", DEFAULT_ISSUE_TYPES)


class ProjectConfig:
    def __init__(self, project_config):
        self.project_name = project_config.get("name", "Unnamed Project")
        self.project_label = project_config.get("label", "(none)")
        self.milestones = project_config.get("milestones", [])
        self.report_dir = project_config.get("report_dir", None)


class ReportOptions(object):
    def __init__(self, verbose=False, project_config=None, jira_config=None, jira=None, report_dir=None):
        self.verbose = verbose
        self.project_config = project_config
        self.jira_config = jira_config
        self.jira = jira
        self.report_dir = report_dir


def load_yaml(config_file, key):
    with open(config_file, 'r') as file:
        config = yaml.safe_load(file)
        return config[key]


def load_project_config(config_file):
    config = load_yaml(config_file, "project")
    return ProjectConfig(config)


def load_jira_config(config_file):
    config = load_yaml(config_file, "jira")
    return JiraConfig(config)
