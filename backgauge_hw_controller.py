from __future__ import annotations

from backgauge_common import (
    AxisConfig,
    AxisRuntimeState,
    StateCallback,
    StatusCallback,
)


class HardwareAxisController:
    """
    Hardware-facing axis controller skeleton.

    This file is intentionally a stub-first implementation.
    The public interface mirrors the simulation controller so the UI can later
    swap between simulation and real hardware with minimal changes.

    Real GPIO / motion code should be added incrementally inside this class,
    not in the UI.
    """

    def calculate_steps(self, distance: float) -> int:
        """
        Convert engineering units to whole step count.
        """
        return int(round(abs(distance) * self.config.steps_per_unit))

    def determine_direction(self, current: float, target: float) -> int | None:
        """
        Return configured direction value for the move.
        Returns None if no movement is needed.
        """
        tol = 0.0005
        if abs(target - current) < tol:
            return None

        if target > current:
            return self.config.cw_value
        return self.config.ccw_value

    def calculate_step_delay(self) -> float:
        """
        Convert max RPM and steps/unit into a basic constant step delay.
        This is placeholder math for fixed-speed motion.
        """
        if self.config.max_rpm <= 0 or self.config.steps_per_unit <= 0:
            raise ValueError(f"{self.config.name}: invalid speed configuration")

        units_per_minute = self.config.max_rpm / self.config.steps_per_unit
        steps_per_minute = units_per_minute * self.config.steps_per_unit

        if steps_per_minute <= 0:
            raise ValueError(f"{self.config.name}: calculated steps per minute is invalid")

        return 60.0 / steps_per_minute

    def plan_move(self, target: float) -> dict:
        """
        Build a simple move plan without touching GPIO.
        Useful for testing math before real motion is added.
        """
        target = self.clamp(target)
        current = self.state.current
        distance = target - current
        steps = self.calculate_steps(distance)
        direction = self.determine_direction(current, target)
        step_delay = self.calculate_step_delay()

        return {
            "axis": self.config.name,
            "current": current,
            "target": target,
            "distance": distance,
            "steps": steps,
            "direction": direction,
            "step_delay": step_delay,
        }


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
        if not self._gpio_ready:
            self._emit_status(f"{self.config.name}: hardware not initialized, simulated move only")

        plan = self.plan_move(self.state.commanded)

        if plan["direction"] is None or plan["steps"] == 0:
            self._emit_status(f"{self.config.name}: already at commanded position")
            self._emit_state()
            return self.state.current

        self.state.is_moving = True
        self._emit_state()

        # Temporary placeholder behavior:
        self.state.current = plan["target"]

        self.state.is_moving = False
        self._emit_status(
            f"{self.config.name}: move planned "
            f"(dist={plan['distance']:.3f}, steps={plan['steps']}, delay={plan['step_delay']:.6f})"
        )
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
