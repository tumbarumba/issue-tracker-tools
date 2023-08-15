from __future__ import annotations


class IssueCounts:
    def __init__(self, pending, in_progress, done):
        self.pending = pending
        self.in_progress = in_progress
        self.done = done
        self.total = pending + in_progress + done

    @classmethod
    def zero(cls) -> IssueCounts:
        return cls(0, 0, 0)

    def __add__(self, other) -> IssueCounts:
        return IssueCounts(self.pending + other.pending,
                           self.in_progress + other.in_progress,
                           self.done + other.done)

    def __eq__(self, other) -> bool:
        return (self.pending == other.pending
                and self.in_progress == other.in_progress
                and self.done == other.done)

    def __str__(self) -> str:
        return f"IssueCounts({self.pending},{self.in_progress},{self.done})"
