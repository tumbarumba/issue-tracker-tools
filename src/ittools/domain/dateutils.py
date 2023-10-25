import numpy as np
import pytz
from datetime import datetime


BUSINESS_HOURS_START = 9
BUSINESS_HOURS_END = 17


def calendar_days(start_time, end_time) -> float | None:
    if not (start_time and end_time):
        return None
    return (
        (
            end_time.astimezone(pytz.UTC) - start_time.astimezone(pytz.UTC)
        ).total_seconds()
        / 60
        / 60
        / 24
    )


def business_days(start_time: datetime, end_time: datetime) -> float | None:
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
