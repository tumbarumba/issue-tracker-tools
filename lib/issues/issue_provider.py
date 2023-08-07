from __future__ import annotations
from typing import List
import abc

from .issue import Epic


class IssueProvider(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def load_project_epics(self: IssueProvider, project_key: str) -> List[Epic]:
        pass
