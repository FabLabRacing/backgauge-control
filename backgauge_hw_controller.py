from __future__ import annotations
import time
import threading

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None
    
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

    def set_direction_output(self, direction: int) -> None:
        """
        Set the hardware direction output.
        """
        if not self._gpio_ready or GPIO is None:
            return

        if self.config.direction_pin is None:
            return

        GPIO.output(self.config.direction_pin, direction)

    def pulse_step_output(self, step_delay: float) -> None:
        """
        Generate one active-low step pulse for common-anode wiring.
        """
        if not self._gpio_ready or GPIO is None:
            if not self.config.simulate_timing:
                return
            effective_delay = step_delay / max(self.config.timing_scale, 1.0)
            time.sleep(effective_delay)
            time.sleep(effective_delay)
            return

        if self.config.step_pin is None:
            return

        effective_delay = step_delay
        if self.config.simulate_timing:
            effective_delay = step_delay / max(self.config.timing_scale, 1.0)

        GPIO.output(self.config.step_pin, GPIO.HIGH)
        time.sleep(effective_delay)
        GPIO.output(self.config.step_pin, GPIO.LOW)
        time.sleep(effective_delay)

        GPIO.output(self.config.step_pin, GPIO.HIGH)
        time.sleep(effective_delay)
        GPIO.output(self.config.step_pin, GPIO.LOW)
        time.sleep(effective_delay)

    def should_stop_for_limit(self, direction: int) -> bool:
        """
        Check whether motion should stop because a relevant limit is active.
        """
        if direction == self.config.cw_value:
            return self.read_max_sensor()
        if direction == self.config.ccw_value:
            return self.read_min_sensor()
        return False

    def execute_step_move(self, target: float) -> float:
        """
        Execute a simple fixed-speed step move using the move plan.
        Updates current position incrementally so the UI can show motion.
        """
        plan = self.plan_move(target)

        if plan["direction"] is None or plan["steps"] == 0:
            self._emit_status(f"{self.config.name}: already at commanded position")
            self._emit_state()
            return self.state.current

        direction = plan["direction"]
        steps = plan["steps"]
        step_delay = plan["step_delay"]

        self.state.is_moving = True
        self.state.last_error = ""
        self._emit_state()

        self.set_direction_output(direction)

        actual_steps = 0
        update_interval = 200  # UI/state refresh every 10 steps

        for _ in range(steps):
            if self.should_stop_for_limit(direction):
                self.state.last_error = f"{self.config.name}: stopped by limit sensor"
                self._emit_status(self.state.last_error)
                break

            self.pulse_step_output(step_delay)
            actual_steps += 1

            step_distance = 1.0 / self.config.steps_per_unit
            if direction == self.config.cw_value:
                self.state.current = self.clamp(self.state.current + step_distance)
            else:
                self.state.current = self.clamp(self.state.current - step_distance)


        self.state.is_moving = False
        self._emit_state()

        if actual_steps == steps:
            self._emit_status(
                f"{self.config.name}: executed move "
                f"(steps={actual_steps}, target={target:.3f})"
            )
        else:
            self._emit_status(
                f"{self.config.name}: partial move "
                f"(steps={actual_steps}/{steps}, current={self.state.current:.3f})"
            )

        return self.state.current

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
        return 0.001

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
        self._move_thread: threading.Thread | None = None
        self._lock = threading.Lock()

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
        Basic GPIO setup for step/dir outputs and limit inputs.
        """
        if GPIO is None:
            self._emit_status(f"{self.config.name}: RPi.GPIO not available")
            self._emit_state()
            return

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)

        if self.config.direction_pin is not None:
            GPIO.setup(self.config.direction_pin, GPIO.OUT)
            GPIO.output(self.config.direction_pin, GPIO.LOW)  # idle state

        if self.config.step_pin is not None:
            GPIO.setup(self.config.step_pin, GPIO.OUT)
            GPIO.output(self.config.step_pin, GPIO.LOW)  # idle state

        if self.config.min_sensor_pin is not None:
            GPIO.setup(self.config.min_sensor_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

        if self.config.max_sensor_pin is not None:
            GPIO.setup(self.config.max_sensor_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

        self._gpio_ready = True
        self._emit_status(f"{self.config.name}: hardware controller initialized")
        self._emit_state()

    def shutdown_gpio(self) -> None:
        """
        Basic GPIO cleanup for this controller.
        """
        if GPIO is not None:
            GPIO.cleanup()

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
        Start a background move if one is not already running.
        Returns the current position immediately.
        """
        with self._lock:
            if self.state.is_moving:
                self._emit_status(f"{self.config.name}: move already in progress")
                self._emit_state()
                return self.state.current

            if not self._gpio_ready:
                self._emit_status(
                    f"{self.config.name}: hardware not initialized, running step-loop placeholder"
                )

            target = self.state.commanded
            self._move_thread = threading.Thread(
                target=self._run_move_thread,
                args=(target,),
                daemon=True,
            )
            self._move_thread.start()

        return self.state.current

    def _run_move_thread(self, target: float) -> None:
        try:
            self.execute_step_move(target)
        except Exception as exc:
            self.state.is_moving = False
            self.state.last_error = f"{self.config.name}: move thread error: {exc}"
            self._emit_status(self.state.last_error)
            self._emit_state()

    def jog(self, delta: float) -> float:
        if self.state.is_moving:
            self._emit_status(f"{self.config.name}: cannot jog while move is active")
            self._emit_state()
            return self.state.current

        target = self.clamp(self.state.current + delta)
        self.state.commanded = target
        self._emit_status(f"{self.config.name}: jog command to {target:.3f}")
        self._emit_state()
        self.move_to_commanded()
        return self.state.current

    def load_preset(self, value: float) -> float:
        value = self.clamp(value)
        self.state.commanded = value
        self._emit_status(f"{self.config.name}: preset loaded ({value:.3f})")
        self._emit_state()
        return value

    def home(self) -> float:
        if self.state.is_moving:
            self._emit_status(f"{self.config.name}: cannot home while move is active")
            self._emit_state()
            return self.state.current

        self.state.commanded = self.config.home_position
        self._emit_status(f"{self.config.name}: homing command issued")
        self._emit_state()
        self.move_to_commanded()
        return self.state.current
        
    def at_home(self) -> bool:
        return abs(self.state.current - self.config.home_position) < 0.0005

    def read_min_sensor(self) -> bool:
        """
        Read the home / minimum travel sensor.
        """
        if not self._gpio_ready or GPIO is None or self.config.min_sensor_pin is None:
            return False
        return bool(GPIO.input(self.config.min_sensor_pin))

    def read_max_sensor(self) -> bool:
        """
        Read the maximum travel sensor.
        """
        if not self._gpio_ready or GPIO is None or self.config.max_sensor_pin is None:
            return False
        return bool(GPIO.input(self.config.max_sensor_pin))

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
