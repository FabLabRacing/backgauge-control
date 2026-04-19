from __future__ import annotations

import threading
import time
from typing import Optional

try:
    import serial
except ImportError:
    serial = None

from backgauge_common import AxisConfig, AxisRuntimeState, StateCallback, StatusCallback


class SerialTransport:
    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        timeout: float = 0.1,
        status_callback: StatusCallback | None = None,
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._status_callback = status_callback
        self._ser = None
        self._lock = threading.Lock()

    def open(self) -> None:
        if serial is None:
            raise RuntimeError("pyserial is not installed")

        self._ser = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,
        )
        self._emit_status(f"ESP32 connected on {self.port} @ {self.baudrate}")

    def close(self) -> None:
        if self._ser is not None:
            try:
                self._ser.close()
            finally:
                self._ser = None
        self._emit_status("ESP32 transport closed")

    def send_line(self, line: str) -> None:
        if self._ser is None:
            raise RuntimeError("Serial transport is not open")

        payload = (line.strip() + "\n").encode("utf-8")
        with self._lock:
            self._ser.write(payload)
            self._ser.flush()

    def read_line(self) -> Optional[str]:
        if self._ser is None:
            return None

        raw = self._ser.readline()
        if not raw:
            return None

        try:
            return raw.decode("utf-8", errors="replace").strip()
        except Exception:
            return None

    def _emit_status(self, message: str) -> None:
        if self._status_callback:
            self._status_callback(message)


class ESP32AxisController:
    def __init__(
        self,
        axis_id: str,
        config: AxisConfig,
        transport: SerialTransport,
        status_callback: StatusCallback | None = None,
        state_callback: StateCallback | None = None,
    ) -> None:
        self.axis_id = axis_id
        self.config = config
        self.transport = transport
        self.state = AxisRuntimeState(
            current=config.home_position,
            commanded=config.home_position,
        )
        self.homed = False
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

    def initialize_gpio(self) -> None:
        self._emit_status(f"{self.config.name}: ESP32 axis ready")
        self._emit_state()

    def shutdown_gpio(self) -> None:
        self.stop_jog()
        self._emit_status(f"{self.config.name}: ESP32 axis shutdown")
        self._emit_state()

    def set_commanded(self, value: float) -> float:
        value = self.clamp(value)
        self.state.commanded = value
        self.transport.send_line(f"SET_CMD,{self.axis_id},{value:.4f}")
        self._emit_status(f"{self.config.name}: commanded set to {value:.3f}")
        self._emit_state()
        return value

    def clear_commanded(self) -> float:
        self.state.commanded = self.config.home_position
        self.transport.send_line(f"SET_CMD,{self.axis_id},{self.state.commanded:.4f}")
        self._emit_status(f"{self.config.name}: commanded cleared")
        self._emit_state()
        return self.state.commanded

    def move_to_commanded(self) -> float:
        self.transport.send_line(f"MOVE,{self.axis_id}")
        self._emit_status(f"{self.config.name}: move requested")
        return self.state.current

    def start_jog(self, direction: int) -> float:
        if direction not in (-1, 1):
            return self.state.current

        sign = "+" if direction > 0 else "-"
        self.transport.send_line(f"JOG_START,{self.axis_id},{sign}")
        self._emit_status(f"{self.config.name}: jog {sign} start")
        return self.state.current

    def stop_jog(self) -> float:
        self.transport.send_line(f"JOG_STOP,{self.axis_id}")
        self._emit_status(f"{self.config.name}: jog stop requested")
        return self.state.current

    def load_preset(self, value: float) -> float:
        value = self.clamp(value)
        self.state.commanded = value
        self.transport.send_line(f"SET_CMD,{self.axis_id},{value:.4f}")
        self._emit_status(f"{self.config.name}: preset loaded ({value:.3f})")
        self._emit_state()
        return value

    def home(self) -> float:
        self.transport.send_line(f"HOME,{self.axis_id}")
        self._emit_status(f"{self.config.name}: homing requested")
        return self.state.current

    @property
    def at_home(self) -> bool:
        return abs(self.state.current - self.config.home_position) < 0.0005

    def apply_state_update(
        self,
        current: float,
        commanded: float,
        is_moving: bool,
        homed: bool,
        last_error: str,
    ) -> None:
        self.state.current = current
        self.state.commanded = commanded
        self.state.is_moving = is_moving
        self.state.last_error = last_error
        self.homed = homed
        self._emit_state()

    def apply_error(self, message: str) -> None:
        self.state.last_error = message
        self._emit_status(message)
        self._emit_state()

    def _emit_status(self, message: str) -> None:
        if self._status_callback:
            self._status_callback(message)

    def _emit_state(self) -> None:
        if self._state_callback:
            self._state_callback()


class BackgaugeESP32Controller:
    def __init__(
        self,
        depth_config: AxisConfig,
        height_config: AxisConfig,
        port: str,
        baudrate: int = 115200,
        status_callback: StatusCallback | None = None,
        state_callback: StateCallback | None = None,
    ) -> None:
        self._status_callback = status_callback
        self._state_callback = state_callback

        self.transport = SerialTransport(
            port=port,
            baudrate=baudrate,
            timeout=0.1,
            status_callback=status_callback,
        )

        self.depth = ESP32AxisController(
            axis_id="D",
            config=depth_config,
            transport=self.transport,
            status_callback=status_callback,
            state_callback=state_callback,
        )

        self.height = ESP32AxisController(
            axis_id="H",
            config=height_config,
            transport=self.transport,
            status_callback=status_callback,
            state_callback=state_callback,
        )

        self._reader_thread: threading.Thread | None = None
        self._stop_reader = threading.Event()
        self._axis_map = {
            "D": self.depth,
            "H": self.height,
        }

    def set_callbacks(
        self,
        status_callback: StatusCallback | None = None,
        state_callback: StateCallback | None = None,
    ) -> None:
        self._status_callback = status_callback
        self._state_callback = state_callback
        self.depth.set_callbacks(status_callback, state_callback)
        self.height.set_callbacks(status_callback, state_callback)

    def initialize_gpio(self) -> None:
        self.transport.open()
        self.depth.initialize_gpio()
        self.height.initialize_gpio()

        self._stop_reader.clear()
        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader_thread.start()

        time.sleep(0.2)
        self.transport.send_line("PING")
        self.transport.send_line("STATUS?")

    def shutdown_gpio(self) -> None:
        self.stop_all()
        self._stop_reader.set()

        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=0.5)

        self.transport.close()

    def home_all(self) -> None:
        self.transport.send_line("HOME_ALL")
        self._emit_status("All axes homing requested")

    def stop_all(self) -> None:
        try:
            self.transport.send_line("STOP,ALL")
        except Exception:
            pass

    def clear_all_errors(self) -> None:
        self.transport.send_line("CLEAR_ERR,ALL")

    def request_status(self) -> None:
        self.transport.send_line("STATUS?")

    def _reader_loop(self) -> None:
        while not self._stop_reader.is_set():
            try:
                line = self.transport.read_line()
                if not line:
                    continue
                self._handle_line(line)
            except Exception as exc:
                self._emit_status(f"ESP32 reader error: {exc}")
                time.sleep(0.2)

    def _handle_line(self, line: str) -> None:
        parts = [p.strip() for p in line.split(",")]
        if not parts:
            return

        kind = parts[0]

        if kind == "OK":
            self._emit_status(f"ESP32: {line}")
            return

        if kind == "ERR" and len(parts) >= 3:
            axis_id = parts[1]
            reason = ",".join(parts[2:])
            axis = self._axis_map.get(axis_id)
            if axis is not None:
                axis.apply_error(f"{axis.config.name}: {reason}")
            else:
                self._emit_status(f"ESP32 error: {reason}")
            return

        if kind == "EVENT" and len(parts) >= 3:
            axis_id = parts[1]
            event_name = ",".join(parts[2:])
            axis = self._axis_map.get(axis_id)
            if axis is not None:
                self._emit_status(f"{axis.config.name}: {event_name}")
            else:
                self._emit_status(f"ESP32 event: {line}")
            return

        if kind == "STATE" and len(parts) >= 3:
            self._handle_state(parts)
            return

        self._emit_status(f"ESP32 unparsed: {line}")

    def _handle_state(self, parts: list[str]) -> None:
        axis_id = parts[1]
        axis = self._axis_map.get(axis_id)
        if axis is None:
            return

        data: dict[str, str] = {}
        for item in parts[2:]:
            if "=" not in item:
                continue
            key, value = item.split("=", 1)
            data[key.strip().upper()] = value.strip()

        try:
            current = float(data.get("CUR", axis.state.current))
            commanded = float(data.get("CMD", axis.state.commanded))
            is_moving = bool(int(data.get("MOV", "0")))
            homed = bool(int(data.get("HOMED", "0")))
            last_error = data.get("ERR", "")
        except Exception as exc:
            self._emit_status(f"STATE parse error: {exc}")
            return

        axis.apply_state_update(
            current=current,
            commanded=commanded,
            is_moving=is_moving,
            homed=homed,
            last_error=last_error,
        )

    def _emit_status(self, message: str) -> None:
        if self._status_callback:
            self._status_callback(message)