from __future__ import annotations
from typing import Any, Dict, List
import os
import yaml


REPORT_DIR_DEFAULT = "~/jirareports"
DEFAULT_STATUSES: list[dict[str, str]] = [
    {"display": "B", "name": "Backlog"},
    {"display": "🔵", "name": "Selected for Development"},
    {"display": "🌑", "name": "Ready for Development"},
    {"display": "🌘", "name": "In Progress"},
    {"display": "🌗", "name": "In Review"},
    {"display": "🌖", "name": "Under Test"},
    {"display": "🌕", "name": "Awaiting Demo"},
    {"display": "🌕", "name": "Done"},
    {"display": "C", "name": "Closed"},
    {"display": "D", "name": "Duplicate"},
]
DEFAULT_ISSUE_TYPES: list[dict[str, str]] = [
    {"display": "📖", "name": "Story"},
    {"display": "🐞", "name": "Bug"},
    {"display": "🔧", "name": "Task"},
]


class IssueTrackerConfig:
    def __init__(self, config: dict[str, Any]) -> None:
        self.provider = config.get("provider", "jira")
        self.report_dir = os.path.expanduser(
            config.get("report_dir", REPORT_DIR_DEFAULT)
        )
        self.jira_config = JiraConfig(config["jira"])
        self.teams = config.get("teams", {})

    @classmethod
    def load(cls, config_file: str) -> IssueTrackerConfig:
        with open(config_file, "r") as file:
            config = yaml.safe_load(file)
            return IssueTrackerConfig(config)


class JiraConfig:
    def __init__(self, jira_config: Dict[str, Any]) -> None:
        self.url: str = jira_config["url"]
        self.statuses: list[dict[str, str]] = jira_config.get(
            "statuses", DEFAULT_STATUSES
        )
        self.issuetypes: list[dict[str, str]] = jira_config.get(
            "issuetypes", DEFAULT_ISSUE_TYPES
        )
        project_keys = jira_config.get("project_keys", [])

        if not project_keys:
            raise ValueError("Unable to find project keys")

        self.project_keys = [str(key) for key in project_keys]


class ProjectConfig:
    def __init__(self, project_config: dict[str, Any]) -> None:
        self.name: str = project_config.get("name", "Unnamed Project")
        self.key: str = project_config.get("key", "(none)")
        self.milestones: List[Dict[str, Any]] = project_config.get("milestones", [])
        self.initial_slope: float = project_config.get("initial_slope", 1.0)

    @classmethod
    def load(cls, config_file: str) -> ProjectConfig:
        with open(config_file, "r") as file:
            config = yaml.safe_load(file)
            return ProjectConfig(config.get("project"))


class ReportOptions(object):
    def __init__(
        self,
        issue_tracker_config: IssueTrackerConfig,
        verbose: bool = False,
    ) -> None:
        self.jira_config = issue_tracker_config.jira_config
        self.report_dir = issue_tracker_config.report_dir
        self.teams = issue_tracker_config.teams
        self.verbose: bool = verbose
