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
    steps_per_unit: float = 200.0
    max_rpm: float = 500.0
    direction_pin: int | None = None
    step_pin: int | None = None
    min_sensor_pin: int | None = None
    max_sensor_pin: int | None = None
    cw_value: int = 0
    ccw_value: int = 1
    simulate_timing: bool = True
    timing_scale: float = 20.0


@dataclass
class AxisRuntimeState:
    current: float = 0.0
    commanded: float = 0.0
    is_moving: bool = False
    last_error: str = ""

    @property
    def in_position(self) -> bool:
        return abs(self.current - self.commanded) < 0.0005
