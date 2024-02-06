from __future__ import annotations

import abc
import numpy as np
from datetime import datetime
from typing import Any, List

from .dateutils import business_days


class IssueState:
    """The state of an issue"""

    def __init__(self, state: str, start_time: datetime):
        self.name = state
        self.start_time = start_time

    def __eq__(self, other: Any) -> bool:
        return self.name == other.name and self.start_time == other.start_time

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"


class Issue(metaclass=abc.ABCMeta):
    """An Issue represents a unit of work"""

    def __init__(self, key: str, summary: str):
        self.key = key
        self.summary = summary

    def __eq__(self, other: Any) -> bool:
        return self.key == other.key

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.key})"

    def time_in_state(self, state_name: str) -> float:
        durations = _durations_for(self.history)
        matching_durations = [duration for state, duration in zip(self.history, durations) if state.name == state_name]
        return sum(matching_durations)

    @property
    @abc.abstractmethod
    def history(self) -> List[IssueState]:
        pass


def _durations_for(states: List[IssueState]):
    start_times = [state.start_time for state in states]
    durations = [business_days(t1, t2) for t1, t2 in zip(start_times[:-1], start_times[1:])]
    durations.append(np.float64(0.0))  # Assume last state has zero time
    return durations
