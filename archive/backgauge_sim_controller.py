from __future__ import annotations

import threading
import time

from backgauge_common import (
    AxisConfig,
    AxisRuntimeState,
    StateCallback,
    StatusCallback,
)


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
        self._jog_thread: threading.Thread | None = None
        self._jog_stop = threading.Event()
        self._lock = threading.Lock()

    def set_callbacks(
        self,
        status_callback: StatusCallback | None = None,
        state_callback: StateCallback | None = None,
    ) -> None:
        self._status_callback = status_callback
        self._state_callback = state_callback
        self._jog_thread: threading.Thread | None = None
        self._jog_stop = threading.Event()
        self._lock = threading.Lock()

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

    def start_jog(self, direction: int) -> float:
        if direction not in (-1, 1):
            return self.state.current

        with self._lock:
            if self.state.is_moving:
                return self.state.current
            self.state.is_moving = True
            self._jog_stop.clear()
            self._jog_thread = threading.Thread(target=self._run_jog_thread, args=(direction,), daemon=True)
            self._jog_thread.start()

        self._emit_status(f"{self.config.name}: jog {'+' if direction > 0 else '-'} start")
        self._emit_state()
        return self.state.current

    def stop_jog(self) -> float:
        self._jog_stop.set()
        self.state.is_moving = False
        self._emit_status(f"{self.config.name}: jog stop")
        self._emit_state()
        return self.state.current

    def _run_jog_thread(self, direction: int) -> None:
        step_size = 1.0 / self.config.steps_per_unit
        step_delay = 0.01

        while not self._jog_stop.is_set():
            next_value = self.clamp(self.state.current + (direction * step_size))
            if abs(next_value - self.state.current) < 0.0000001:
                break
            self.state.current = next_value
            self.state.commanded = self.state.current
            self._emit_state()
            time.sleep(step_delay)

        self.state.is_moving = False
        self.state.commanded = self.state.current
        self._emit_state()

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
