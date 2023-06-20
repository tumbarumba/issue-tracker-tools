from __future__ import annotations
from typing import Any, Dict
import os
import yaml


DEFAULT_STATUSES = [
    {"display": "🔵", "name": "Backlog"},
    {"display": "🌑", "name": "Selected for Development"},
    {"display": "🌘", "name": "Ready for Development"},
    {"display": "🌗", "name": "In Progress"},
    {"display": "🌖", "name": "In Review"},
    {"display": "🌕", "name": "Awaiting Merge"},
    {"display": "🌕", "name": "Under Test"},
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
    def __init__(self: JiraConfig, jira_config: Dict[str, Any]):
        self.url: str = jira_config['url']
        self.statuses: Dict[str, Dict[str, str]] = jira_config.get("statuses", DEFAULT_STATUSES)
        self.issuetypes: Dict[str, Dict[str, str]] = jira_config.get("issuetypes", DEFAULT_ISSUE_TYPES)


class ProjectConfig:
    def __init__(self: ProjectConfig, project_config: Dict[str, Any]):
        self.project_name: str = project_config.get("name", "Unnamed Project")
        self.project_label: str = project_config.get("label", "(none)")
        self.milestones: Dict[str, Any] = project_config.get("milestones", [])
        self.report_dir: str | None = project_config.get("report_dir", None)


REPORT_DIR_DEFAULT = "~/jirareports"


class ReportOptions(object):
    def __init__(
            self: ReportOptions,
            verbose: bool = False,
            project_config: ProjectConfig = None,
            jira_config: JiraConfig = None):
        self.verbose: bool = verbose
        self.project_config: ProjectConfig = project_config
        self.jira_config: JiraConfig = jira_config
        self.report_dir: str = self.lookup_report_dir()

    def lookup_report_dir(self) -> str:
        dir = self.project_config.report_dir or REPORT_DIR_DEFAULT
        if "~" in dir:
            dir = os.path.expanduser(dir)
        if self.verbose:
            print(f"Using report_dir {dir}")
        return dir


def load_yaml(config_file: str, key: str) -> Dict[str, Any]:
    with open(config_file, 'r') as file:
        config = yaml.safe_load(file)
        return config[key]


def load_project_config(config_file: str) -> ProjectConfig:
    config_data = load_yaml(config_file, "project")
    return ProjectConfig(config_data)


def load_jira_config(config_file: str) -> JiraConfig:
    config_data = load_yaml(config_file, "jira")
    return JiraConfig(config_data)
