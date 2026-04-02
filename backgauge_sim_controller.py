from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


StatusCallback = Callable[[str], None]
StateCallback = Callable[[], None]


@dataclass
class AxisConfig:
    name: str
    min_limit: float
    max_limit: float
    jog_steps: tuple[float, float, float] = (0.100, 0.010, 0.001)
    presets: list[tuple[str, float]] = field(default_factory=list)
    home_position: float = 0.0


@dataclass
class AxisRuntimeState:
    current: float = 0.0
    commanded: float = 0.0

    @property
    def in_position(self) -> bool:
        return abs(self.current - self.commanded) < 0.0005


class SimAxisController:
    def __init__(
        self,
        config: AxisConfig,
        status_callback: StatusCallback | None = None,
        state_callback: StateCallback | None = None,
    ) -> None:
        self.config = config
        self.state = AxisRuntimeState(
            current=config.home_position,
            commanded=config.home_position,
        )
        self._status_callback = status_callback
        self._state_callback = state_callback

    def set_callbacks(
        self,
        status_callback: StatusCallback | None = None,
        state_callback: StateCallback | None = None,
    ) -> None:
        self._status_callback = status_callback
        self._state_callback = state_callback

    def clamp(self, value: float) -> float:
        return max(self.config.min_limit, min(self.config.max_limit, value))

    def set_commanded(self, value: float) -> float:
        value = self.clamp(value)
        self.state.commanded = value
        self._emit_status(f"{self.config.name}: commanded set to {value:.3f}")
        self._emit_state()
        return value

    def clear_commanded(self) -> float:
        self.state.commanded = 0.0
        self._emit_status(f"{self.config.name}: commanded cleared")
        self._emit_state()
        return self.state.commanded

    def move_to_commanded(self) -> float:
        self.state.current = self.clamp(self.state.commanded)
        self._emit_status(f"{self.config.name}: simulated move to {self.state.current:.3f}")
        self._emit_state()
        return self.state.current

    def jog(self, delta: float) -> float:
        self.state.current = self.clamp(self.state.current + delta)
        self.state.commanded = self.state.current
        self._emit_status(f"{self.config.name}: jogged to {self.state.current:.3f}")
        self._emit_state()
        return self.state.current

    def load_preset(self, value: float) -> float:
        value = self.clamp(value)
        self.state.commanded = value
        self._emit_status(f"{self.config.name}: preset loaded ({value:.3f})")
        self._emit_state()
        return value

    def home(self) -> float:
        self.state.current = self.config.home_position
        self.state.commanded = self.config.home_position
        self._emit_status(f"{self.config.name}: homed")
        self._emit_state()
        return self.state.current

    @property
    def at_home(self) -> bool:
        return abs(self.state.current - self.config.home_position) < 0.0005

    def _emit_status(self, message: str) -> None:
        if self._status_callback:
            self._status_callback(message)

    def _emit_state(self) -> None:
        if self._state_callback:
            self._state_callback()


class BackgaugeSimController:
    def __init__(
        self,
        depth_config: AxisConfig,
        height_config: AxisConfig,
        status_callback: StatusCallback | None = None,
        state_callback: StateCallback | None = None,
    ) -> None:
        self.depth = SimAxisController(depth_config, status_callback, state_callback)
        self.height = SimAxisController(height_config, status_callback, state_callback)

    def set_callbacks(
        self,
        status_callback: StatusCallback | None = None,
        state_callback: StateCallback | None = None,
    ) -> None:
        self.depth.set_callbacks(status_callback, state_callback)
        self.height.set_callbacks(status_callback, state_callback)

    def home_all(self) -> None:
        self.depth.home()
        self.height.home()
