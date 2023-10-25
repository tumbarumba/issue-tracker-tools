from __future__ import annotations

import abc
import numpy as np
from datetime import datetime
from typing import Any, List


class IssueState:
    """The state of an issue"""

    def __init__(self: IssueState, state: str, start_time: datetime):
        self.name = state
        self.start_time = start_time

    def __eq__(self: IssueState, other: Any) -> bool:
        return self.name == other.name and self.start_time == other.start_time

    def __repr__(self: IssueState) -> str:
        return f"{self.__class__.__name__}({self.name})"


class Issue(metaclass=abc.ABCMeta):
    """An Issue represents a unit of work"""

    def __init__(self: Issue, key: str, summary: str):
        self.key = key
        self.summary = summary

    def __eq__(self: Issue, other: Any) -> bool:
        return self.key == other.key

    def __repr__(self: Issue) -> str:
        return f"{self.__class__.__name__}({self.key})"

    def time_in_state(self: Issue, state_name: str) -> float:
        durations = _durations_for(self.history)
        matching_durations = [duration for state, duration in zip(self.history, durations) if state.name == state_name]
        return sum(matching_durations)

    @property
    @abc.abstractmethod
    def history(self: Issue) -> List[IssueState]:
        pass


def _durations_for(states: List[IssueState]):
    start_times = [state.start_time for state in states]
    durations = [_business_days(t1, t2) for t1, t2 in zip(start_times[:-1], start_times[1:])]
    durations.append(np.float64(0.0))  # Assume last state has zero time
    return durations


BUSINESS_HOURS_START = 9
BUSINESS_HOURS_END = 17


def _business_days(start_time: datetime, end_time: datetime) -> float | None:
    if not (start_time and end_time):
        return None
    bus_days = np.busday_count(start_time.date(), end_time.date())
    bus_hours = _hours_in_working_day(start_time, end_time)
    return bus_days + (bus_hours / 8)


def _hours_in_working_day(start_time: datetime, end_time: datetime) -> float:
    bus_hours = _end_hours(end_time) - _start_hours(start_time)
    if bus_hours < -8:
        bus_hours = (bus_hours + 24) * -1
    if bus_hours > 8:
        bus_hours = 8
    return bus_hours


def _start_hours(start_time) -> float:
    start_hours = start_time.hour + start_time.minute / 60
    return min(start_hours, BUSINESS_HOURS_END)


def _end_hours(end_time) -> float:
    end_hours = end_time.hour + end_time.minute / 60
    return max(end_hours, BUSINESS_HOURS_START)
