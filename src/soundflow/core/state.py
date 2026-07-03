from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from threading import RLock
from typing import Callable


class DictationState(Enum):
    IDLE = auto()
    RECORDING = auto()
    PAUSED = auto()
    DRAINING = auto()
    ERROR = auto()


class InvalidTransition(RuntimeError):
    pass


@dataclass(frozen=True)
class StateChange:
    previous: DictationState
    current: DictationState
    reason: str


class DictationStateMachine:
    """Small, thread-safe state machine shared by buttons and hotkeys."""

    def __init__(self, on_change: Callable[[StateChange], None] | None = None) -> None:
        self._state = DictationState.IDLE
        self._lock = RLock()
        self._on_change = on_change

    @property
    def state(self) -> DictationState:
        with self._lock:
            return self._state

    def start(self, reason: str = "start") -> None:
        self._move({DictationState.IDLE, DictationState.ERROR}, DictationState.RECORDING, reason)

    def stop(self, reason: str = "stop") -> None:
        self._move(
            {DictationState.RECORDING, DictationState.PAUSED},
            DictationState.DRAINING,
            reason,
        )

    def drained(self) -> None:
        self._move({DictationState.DRAINING}, DictationState.IDLE, "drained")

    def pause(self) -> None:
        self._move({DictationState.RECORDING}, DictationState.PAUSED, "pause")

    def resume(self) -> None:
        self._move({DictationState.PAUSED}, DictationState.RECORDING, "resume")

    def fail(self, reason: str) -> None:
        with self._lock:
            previous = self._state
            self._state = DictationState.ERROR
        self._notify(StateChange(previous, DictationState.ERROR, reason))

    def reset(self) -> None:
        self._move(
            {
                DictationState.IDLE,
                DictationState.RECORDING,
                DictationState.PAUSED,
                DictationState.DRAINING,
                DictationState.ERROR,
            },
            DictationState.IDLE,
            "reset",
        )

    def toggle(self) -> None:
        state = self.state
        if state in {DictationState.IDLE, DictationState.ERROR}:
            self.start("toggle")
        elif state in {DictationState.RECORDING, DictationState.PAUSED}:
            self.stop("toggle")

    def _move(
        self,
        allowed: set[DictationState],
        target: DictationState,
        reason: str,
    ) -> None:
        with self._lock:
            previous = self._state
            if previous not in allowed:
                raise InvalidTransition(f"Cannot move from {previous.name} to {target.name}")
            if previous is target:
                return
            self._state = target
        self._notify(StateChange(previous, target, reason))

    def _notify(self, change: StateChange) -> None:
        if self._on_change:
            self._on_change(change)

