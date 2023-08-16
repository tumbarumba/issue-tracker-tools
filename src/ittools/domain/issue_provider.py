from __future__ import annotations
from typing import List
import abc

from .epic import Epic


class IssueProvider(metaclass=abc.ABCMeta):
    """A service that can load issues from an external service or database"""

    @abc.abstractmethod
    def load_project_epics(self: IssueProvider, project_key: str) -> List[Epic]:
        pass
