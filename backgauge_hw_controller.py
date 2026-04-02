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


@dataclass
class AxisRuntimeState:
    current: float = 0.0
    commanded: float = 0.0
    is_moving: bool = False
    last_error: str = ""

    @property
    def in_position(self) -> bool:
        return abs(self.current - self.commanded) < 0.0005


class HardwareAxisController:
    """
    Hardware-facing axis controller skeleton.

    This file is intentionally a stub-first implementation.
    The public interface mirrors the simulation controller so the UI can later
    swap between simulation and real hardware with minimal changes.

    Real GPIO / motion code should be added incrementally inside this class,
    not in the UI.
    """

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
        self._gpio_ready = False

    def set_callbacks(
        self,
        status_callback: StatusCallback | None = None,
        state_callback: StateCallback | None = None,
    ) -> None:
        self._status_callback = status_callback
        self._state_callback = state_callback

    def clamp(self, value: float) -> float:
        return max(self.config.min_limit, min(self.config.max_limit, value))

    def initialize_gpio(self) -> None:
        """
        Placeholder for future GPIO setup.

        Future work:
        - import GPIO library
        - set GPIO mode
        - configure step/dir pins
        - configure limit switch inputs
        - configure driver enable if needed
        """
        self._gpio_ready = True
        self._emit_status(f"{self.config.name}: hardware controller initialized")
        self._emit_state()

    def shutdown_gpio(self) -> None:
        """
        Placeholder for future GPIO cleanup.
        """
        self._gpio_ready = False
        self._emit_status(f"{self.config.name}: hardware controller shutdown")
        self._emit_state()

    def set_commanded(self, value: float) -> float:
        value = self.clamp(value)
        self.state.commanded = value
        self._emit_status(f"{self.config.name}: commanded set to {value:.3f}")
        self._emit_state()
        return value

    def clear_commanded(self) -> float:
        self.state.commanded = self.config.home_position
        self._emit_status(f"{self.config.name}: commanded cleared")
        self._emit_state()
        return self.state.commanded

    def move_to_commanded(self) -> float:
        """
        Placeholder for real move logic.

        Future work:
        - calculate distance to move
        - determine direction
        - convert distance to steps
        - perform stepped move with timing control
        - stop on limit sensor
        - update current from actual move result
        """
        if not self._gpio_ready:
            self._emit_status(f"{self.config.name}: hardware not initialized, simulated move only")

        self.state.is_moving = True
        self._emit_state()

        # Temporary placeholder behavior:
        self.state.current = self.clamp(self.state.commanded)

        self.state.is_moving = False
        self._emit_status(f"{self.config.name}: hardware move placeholder to {self.state.current:.3f}")
        self._emit_state()
        return self.state.current

    def jog(self, delta: float) -> float:
        target = self.clamp(self.state.current + delta)
        self.state.commanded = target
        self._emit_status(f"{self.config.name}: jog command to {target:.3f}")
        self._emit_state()
        return self.move_to_commanded()

    def load_preset(self, value: float) -> float:
        value = self.clamp(value)
        self.state.commanded = value
        self._emit_status(f"{self.config.name}: preset loaded ({value:.3f})")
        self._emit_state()
        return value

    def home(self) -> float:
        """
        Placeholder for future homing logic.

        Future work:
        - move toward home sensor
        - stop when sensor is active
        - optionally back off and re-approach slowly
        - set current = home_position
        - set commanded = home_position
        """
        self.state.is_moving = True
        self._emit_state()

        self.state.current = self.config.home_position
        self.state.commanded = self.config.home_position

        self.state.is_moving = False
        self._emit_status(f"{self.config.name}: hardware home placeholder complete")
        self._emit_state()
        return self.state.current

    @property
    def at_home(self) -> bool:
        return abs(self.state.current - self.config.home_position) < 0.0005

    def read_min_sensor(self) -> bool:
        """
        Placeholder for future home / min limit sensor read.
        """
        return False

    def read_max_sensor(self) -> bool:
        """
        Placeholder for future max travel sensor read.
        """
        return False

    def _emit_status(self, message: str) -> None:
        if self._status_callback:
            self._status_callback(message)

    def _emit_state(self) -> None:
        if self._state_callback:
            self._state_callback()


class BackgaugeHardwareController:
    def __init__(
        self,
        depth_config: AxisConfig,
        height_config: AxisConfig,
        status_callback: StatusCallback | None = None,
        state_callback: StateCallback | None = None,
    ) -> None:
        self.depth = HardwareAxisController(depth_config, status_callback, state_callback)
        self.height = HardwareAxisController(height_config, status_callback, state_callback)

    def set_callbacks(
        self,
        status_callback: StatusCallback | None = None,
        state_callback: StateCallback | None = None,
    ) -> None:
        self.depth.set_callbacks(status_callback, state_callback)
        self.height.set_callbacks(status_callback, state_callback)

    def initialize_gpio(self) -> None:
        self.depth.initialize_gpio()
        self.height.initialize_gpio()

    def shutdown_gpio(self) -> None:
        self.depth.shutdown_gpio()
        self.height.shutdown_gpio()

    def home_all(self) -> None:
        self.depth.home()
        self.height.home()
