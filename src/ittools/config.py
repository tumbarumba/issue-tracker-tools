from __future__ import annotations
from typing import Any, Dict, List
import os
import yaml


REPORT_DIR_DEFAULT = "~/jirareports"
DEFAULT_STATUSES = [
    {"display": "B", "name": "Backlog"},
    {"display": "🔵", "name": "Selected for Development"},
    {"display": "🌑", "name": "Ready for Development"},
    {"display": "🌘", "name": "In Progress"},
    {"display": "🌗", "name": "In Review"},
    {"display": "🌗", "name": "Awaiting Merge"},
    {"display": "🌖", "name": "Under Test"},
    {"display": "🌕", "name": "Awaiting Demo"},
    {"display": "🌕", "name": "Done"},
    {"display": "C", "name": "Closed"},
    {"display": "D", "name": "Duplicate"},
]
DEFAULT_ISSUE_TYPES = [
    {"display": "📖", "name": "Story"},
    {"display": "🐞", "name": "Bug"},
    {"display": "🔧", "name": "Task"},
]


class IssueTrackerConfig:
    def __init__(self, config: Dict[str, Any]):
        self.provider = config.get("provider", "jira")
        self.report_dir = os.path.expanduser(
            config.get("report_dir", REPORT_DIR_DEFAULT)
        )
        self.jira_config = JiraConfig(config["jira"])
        self.projects = build_projects(config.get("projects", []))


def build_projects(project_configs: List[Dict[str, Any]]):
    projects = map(
        lambda project_config: ProjectConfig(project_config),
        project_configs,
    )
    return dict((project.key, project) for project in projects)


class JiraConfig:
    def __init__(self, jira_config: Dict[str, Any]):
        self.url: str = jira_config["url"]
        self.statuses: Dict[str, Dict[str, str]] = jira_config.get(
            "statuses", DEFAULT_STATUSES
        )
        self.issuetypes: Dict[str, Dict[str, str]] = jira_config.get(
            "issuetypes", DEFAULT_ISSUE_TYPES
        )


class ProjectConfig:
    def __init__(self, project_config: Dict[str, Any]):
        self.name: str = project_config.get("name", "Unnamed Project")
        self.key: str = project_config.get("key", "(none)")
        self.milestones: List[Dict[str, Any]] = project_config.get("milestones", [])


class ReportOptions(object):
    def __init__(
        self,
        issue_tracker_config: IssueTrackerConfig,
        verbose: bool = False,
    ):
        self.jira_config = issue_tracker_config.jira_config
        self.project_configs = issue_tracker_config.projects
        self.report_dir = issue_tracker_config.report_dir
        self.verbose: bool = verbose


def load_issue_tracker_config(config_file: str) -> IssueTrackerConfig:
    with open(config_file, "r") as file:
        config = yaml.safe_load(file)
        return IssueTrackerConfig(config)
