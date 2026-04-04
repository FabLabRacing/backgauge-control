import customtkinter as ctk
from dataclasses import dataclass, field

from backgauge_common import AxisConfig
from backgauge_sim_controller import BackgaugeSimController
from backgauge_hw_controller import BackgaugeHardwareController


MODE = "HW"  # "SIM" or "HW"

SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
PANEL_PADX = 18
PANEL_PADY = 18
TITLE_FONT = ("Arial", 34, "bold")
SECTION_FONT = ("Arial", 20, "bold")
LABEL_FONT = ("Arial", 18)
CURRENT_FONT = ("Arial", 56, "bold")
ENTRY_FONT = ("Arial", 34)
BUTTON_FONT = ("Arial", 24, "bold")
STATUS_FONT = ("Arial", 22, "bold")
BUTTON_HEIGHT = 72
SMALL_BUTTON_HEIGHT = 64


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


@dataclass
class AxisState:
    name: str
    current: float = 0.0
    commanded: str = "0.000"
    min_limit: float = 0.0
    max_limit: float = 240.0
    jog_steps: tuple[float, float, float] = (0.100, 0.010, 0.001)
    presets: list[tuple[str, float]] = field(default_factory=list)


class CalculatorPanel(ctk.CTkFrame):
    def __init__(self, master, on_send_depth, on_send_height):
        super().__init__(master)
        self.on_send_depth = on_send_depth
        self.on_send_height = on_send_height
        self.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.display = ctk.CTkEntry(self, height=76, font=ENTRY_FONT, justify="right")
        self.display.grid(row=0, column=0, columnspan=4, sticky="ew", padx=12, pady=(12, 10))
        self.display.insert(0, "0")

        buttons = [
            ("7", 1, 0), ("8", 1, 1), ("9", 1, 2), ("/", 1, 3),
            ("4", 2, 0), ("5", 2, 1), ("6", 2, 2), ("*", 2, 3),
            ("1", 3, 0), ("2", 3, 1), ("3", 3, 2), ("-", 3, 3),
            ("=", 4, 0), ("0", 4, 1), (".", 4, 2), ("+", 4, 3),
        ]

        for text, row, col in buttons:
            ctk.CTkButton(
                self,
                text=text,
                height=SMALL_BUTTON_HEIGHT,
                font=BUTTON_FONT,
                command=lambda value=text: self.handle_button(value),
            ).grid(row=row, column=col, sticky="nsew", padx=6, pady=6)

        ctk.CTkButton(self, text="Clear", height=SMALL_BUTTON_HEIGHT, command=self.clear).grid(
            row=5, column=0, columnspan=2, sticky="ew", padx=6, pady=(10, 6)
        )
        ctk.CTkButton(self, text="in → mm", height=SMALL_BUTTON_HEIGHT, command=self.in_to_mm).grid(
            row=5, column=2, sticky="ew", padx=6, pady=(10, 6)
        )
        ctk.CTkButton(self, text="mm → in", height=SMALL_BUTTON_HEIGHT, command=self.mm_to_in).grid(
            row=5, column=3, sticky="ew", padx=6, pady=(10, 6)
        )

        ctk.CTkButton(self, text="Grab to Depth", height=BUTTON_HEIGHT, command=self.send_to_depth).grid(
            row=6, column=0, columnspan=2, sticky="ew", padx=6, pady=(6, 12)
        )
        ctk.CTkButton(self, text="Grab to Height", height=BUTTON_HEIGHT, command=self.send_to_height).grid(
            row=6, column=2, columnspan=2, sticky="ew", padx=6, pady=(6, 12)
        )

    def get_value(self) -> float | None:
        try:
            return float(self.display.get())
        except ValueError:
            return None

    def set_value(self, value: float) -> None:
        self.display.delete(0, "end")
        self.display.insert(0, f"{value:.4f}".rstrip("0").rstrip("."))

    def clear(self) -> None:
        self.display.delete(0, "end")
        self.display.insert(0, "0")

    def handle_button(self, value: str) -> None:
        if value == "=":
            self.evaluate()
            return

        current = self.display.get().strip()
        if current == "0" and value not in (".", "+", "-", "*", "/"):
            current = ""

        self.display.delete(0, "end")
        self.display.insert(0, current + value)

    def evaluate(self) -> None:
        expression = self.display.get().strip()
        try:
            result = eval(expression, {"__builtins__": {}}, {})
            self.set_value(float(result))
        except Exception:
            self.display.delete(0, "end")
            self.display.insert(0, "ERR")

    def in_to_mm(self) -> None:
        value = self.get_value()
        if value is not None:
            self.set_value(value * 25.4)

    def mm_to_in(self) -> None:
        value = self.get_value()
        if value is not None:
            self.set_value(value / 25.4)

    def send_to_depth(self) -> None:
        value = self.get_value()
        if value is not None:
            self.on_send_depth(value)
            self.clear()

    def send_to_height(self) -> None:
        value = self.get_value()
        if value is not None:
            self.on_send_height(value)
            self.clear()


class BackgaugeSchematic(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.depth_current = 0.0
        self.depth_commanded = 0.0
        self.height_current = 0.0
        self.height_commanded = 0.0
        self.depth_max = 240.0
        self.height_max = 150.0
        self.in_position = True

        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text="Backgauge View", font=SECTION_FONT).grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 6)
        )

        self.canvas = ctk.CTkCanvas(self, height=300, highlightthickness=0, bd=0)
        self.canvas.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 10))
        self.canvas.bind("<Configure>", lambda event: self.redraw())

        self.legend = ctk.CTkLabel(
            self,
            text="Green = current at commanded   |   Orange = current not at commanded   |   White = commanded",
            font=("Arial", 14),
            anchor="w",
        )
        self.legend.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))

    def set_values(self, depth_current: float, depth_commanded: float, height_current: float, height_commanded: float, in_position: bool):
        self.depth_current = depth_current
        self.depth_commanded = depth_commanded
        self.height_current = height_current
        self.height_commanded = height_commanded
        self.in_position = in_position
        self.redraw()

    def map_depth(self, value: float, x0: float, x1: float) -> float:
        return x0 + (max(0.0, min(self.depth_max, value)) / self.depth_max) * (x1 - x0) if self.depth_max > 0 else x0

    def map_height(self, value: float, y0: float, y1: float) -> float:
        return y1 - (max(0.0, min(self.height_max, value)) / self.height_max) * (y1 - y0) if self.height_max > 0 else y1

    def redraw(self):
        c = self.canvas
        c.delete("all")
        w = max(c.winfo_width(), 400)
        h = max(c.winfo_height(), 260)
        bg = "#20232a"
        panel = "#2b2f38"
        steel = "#7f8c9a"
        white = "#f2f2f2"
        orange = "#ff9f43"
        green = "#31d67b"
        grid = "#3a404b"
        c.configure(bg=bg)

        left = 50
        right = w - 50
        top = 35
        bottom = h - 35
        bed_y = bottom - 28

        c.create_rectangle(left, bed_y, right - 30, bed_y + 20, fill=steel, outline=steel)
        c.create_polygon(right - 30, bed_y, right, bed_y - 14, right, bed_y + 6, right - 30, bed_y + 20, fill="#687381", outline="#687381")

        ref_x = left + 70
        c.create_rectangle(ref_x - 12, top + 20, ref_x + 12, bed_y, fill=panel, outline=steel, width=2)
        c.create_line(ref_x + 12, top + 20, ref_x + 30, top + 8, fill=steel, width=2)
        c.create_line(ref_x + 12, bed_y, ref_x + 30, bed_y - 12, fill=steel, width=2)
        c.create_line(ref_x + 30, top + 8, ref_x + 30, bed_y - 12, fill=steel, width=2)

        rail_x0 = ref_x + 55
        rail_x1 = right - 85
        c.create_line(rail_x0, bed_y - 55, rail_x1, bed_y - 55, fill=grid, width=4)
        c.create_line(rail_x0, top + 10, rail_x0, bed_y - 55, fill=grid, dash=(4, 4))

        cmd_x = self.map_depth(self.depth_commanded, rail_x0, rail_x1)
        cmd_y = self.map_height(self.height_commanded, top + 25, bed_y - 65)
        c.create_line(cmd_x, top + 10, cmd_x, bed_y - 55, fill=white, dash=(6, 4), width=2)
        c.create_line(rail_x0, cmd_y, rail_x1, cmd_y, fill=white, dash=(6, 4), width=2)
        c.create_oval(cmd_x - 7, cmd_y - 7, cmd_x + 7, cmd_y + 7, fill=white, outline=white)

        cur_x = self.map_depth(self.depth_current, rail_x0, rail_x1)
        cur_y = self.map_height(self.height_current, top + 25, bed_y - 65)
        current_color = green if self.in_position else orange
        c.create_rectangle(cur_x - 18, cur_y - 12, cur_x + 18, cur_y + 12, fill=current_color, outline=current_color)
        c.create_line(cur_x, cur_y + 12, cur_x, bed_y - 4, fill=current_color, width=3)
        c.create_polygon(cur_x, bed_y - 4, cur_x + 16, bed_y + 6, cur_x + 16, bed_y - 14, fill=current_color, outline=current_color)

        c.create_text(left, top, text="Height", fill=white, anchor="w", font=("Arial", 14, "bold"))
        c.create_text(left, bed_y + 28, text=f"Depth cur/cmd: {self.depth_current:.3f} / {self.depth_commanded:.3f}", fill=white, anchor="w", font=("Arial", 13))
        c.create_text(left, bed_y + 48, text=f"Height cur/cmd: {self.height_current:.3f} / {self.height_commanded:.3f}", fill=white, anchor="w", font=("Arial", 13))


class AxisPanel(ctk.CTkFrame):
    def __init__(self, master, axis: AxisState, controller_axis, change_callback=None):
        super().__init__(master)
        self.axis = axis
        self.controller_axis = controller_axis
        self.change_callback = change_callback
        self.grid_columnconfigure((0, 1, 2), weight=1)

        self.title_label = ctk.CTkLabel(self, text=axis.name, font=TITLE_FONT)
        self.title_label.grid(row=0, column=0, columnspan=2, padx=12, pady=(12, 8), sticky="w")

        self.at_pos_label = ctk.CTkLabel(self, text="", font=("Arial", 20, "bold"))
        self.at_pos_label.grid(row=0, column=2, padx=12, pady=(12, 8), sticky="e")

        ctk.CTkLabel(self, text="Current", font=LABEL_FONT).grid(row=1, column=0, padx=12, pady=(4, 0), sticky="w")
        self.current_label = ctk.CTkLabel(self, text="0.000", font=CURRENT_FONT, text_color="green")
        self.current_label.grid(row=2, column=0, columnspan=3, padx=12, pady=(0, 12), sticky="w")

        ctk.CTkLabel(self, text="Commanded", font=LABEL_FONT).grid(row=3, column=0, padx=12, pady=(4, 0), sticky="w")
        self.commanded_entry = ctk.CTkEntry(self, height=76, font=ENTRY_FONT, justify="right")
        self.commanded_entry.grid(row=4, column=0, columnspan=3, sticky="ew", padx=12, pady=(0, 12))

        ctk.CTkButton(self, text=f"Move to {axis.name}", height=BUTTON_HEIGHT, command=self.move_to_commanded).grid(
            row=5, column=0, columnspan=2, sticky="ew", padx=(12, 6), pady=6
        )
        ctk.CTkButton(self, text="Clear", height=BUTTON_HEIGHT, command=self.clear_commanded).grid(
            row=5, column=2, sticky="ew", padx=(6, 12), pady=6
        )

        jog_frame = ctk.CTkFrame(self)
        jog_frame.grid(row=6, column=0, columnspan=3, sticky="ew", padx=12, pady=(12, 8))
        jog_frame.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(jog_frame, text="Jog +", font=SECTION_FONT).grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(8, 4))
        for idx, step in enumerate(axis.jog_steps):
            ctk.CTkButton(jog_frame, text=f"+{step:0.3f}", height=SMALL_BUTTON_HEIGHT, command=lambda value=step: self.jog(value)).grid(
                row=1, column=idx, sticky="ew", padx=6, pady=6
            )

        ctk.CTkLabel(jog_frame, text="Jog -", font=SECTION_FONT).grid(row=2, column=0, columnspan=3, sticky="w", padx=10, pady=(10, 4))
        for idx, step in enumerate(axis.jog_steps):
            ctk.CTkButton(jog_frame, text=f"-{step:0.3f}", height=SMALL_BUTTON_HEIGHT, command=lambda value=step: self.jog(-value)).grid(
                row=3, column=idx, sticky="ew", padx=6, pady=(6, 10)
            )

        preset_frame = ctk.CTkFrame(self)
        preset_frame.grid(row=7, column=0, columnspan=3, sticky="ew", padx=12, pady=(8, 12))
        preset_frame.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(preset_frame, text="Presets", font=SECTION_FONT).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(8, 6))

        for idx, (label, value) in enumerate(axis.presets):
            ctk.CTkButton(preset_frame, text=label, height=SMALL_BUTTON_HEIGHT, command=lambda v=value: self.set_commanded(v)).grid(
                row=1 + idx // 2, column=idx % 2, sticky="ew", padx=6, pady=6
            )

        self.refresh_from_controller()

    @staticmethod
    def format_value(value: float) -> str:
        return f"{value:.3f}"

    def refresh_from_controller(self) -> None:
        state = self.controller_axis.state
        self.current_label.configure(text=self.format_value(state.current))
        self.commanded_entry.delete(0, "end")
        self.commanded_entry.insert(0, self.format_value(state.commanded))
        self.update_colors()

    def update_colors(self):
        state = self.controller_axis.state
        tol = 0.0005
        at_home_position = abs(state.current - self.controller_axis.config.home_position) < tol
        commanded_is_home = abs(state.commanded - self.controller_axis.config.home_position) < tol

        if state.is_moving:
            self.current_label.configure(text_color="orange")
            self.at_pos_label.configure(text="MOVING", text_color="orange")
        elif at_home_position and commanded_is_home:
            self.current_label.configure(text_color="green")
            self.at_pos_label.configure(text="HOME", text_color="green")
        elif state.in_position:
            self.current_label.configure(text_color="green")
            self.at_pos_label.configure(text="AT POSITION", text_color="green")
        else:
            self.current_label.configure(text_color="orange")
            self.at_pos_label.configure(text="NOT IN POSITION", text_color="orange")

    def set_commanded(self, value: float) -> None:
        self.controller_axis.load_preset(value)
        self.refresh_from_controller()
        if self.change_callback:
            self.change_callback()

    def clear_commanded(self) -> None:
        self.controller_axis.clear_commanded()
        self.refresh_from_controller()
        if self.change_callback:
            self.change_callback()

    def move_to_commanded(self) -> None:
        try:
            value = float(self.commanded_entry.get())
        except ValueError:
            return
        self.controller_axis.set_commanded(value)
        self.controller_axis.move_to_commanded()
        self.refresh_from_controller()
        if self.change_callback:
            self.change_callback()

    def jog(self, delta: float) -> None:
        self.controller_axis.jog(delta)
        self.refresh_from_controller()
        if self.change_callback:
            self.change_callback()


class HomePanel(ctk.CTkFrame):
    def __init__(self, master, home_all, home_depth, home_height):
        super().__init__(master)
        self.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(self, text="Home All", height=BUTTON_HEIGHT, command=home_all).grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        ctk.CTkButton(self, text="Home Depth", height=BUTTON_HEIGHT, command=home_depth).grid(row=0, column=1, sticky="ew", padx=8, pady=8)
        ctk.CTkButton(self, text="Home Height", height=BUTTON_HEIGHT, command=home_height).grid(row=0, column=2, sticky="ew", padx=8, pady=8)


class BackgaugeApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Backgauge Control")
        self.attributes("-fullscreen", True)
        self.bind("<Escape>", lambda event: self.destroy())

        self.depth_axis = AxisState(
            name="Stop Depth",
            min_limit=0.0,
            max_limit=240.0,
            presets=[("Bend 1", 12.000), ("Bend 2", 18.500), ("Bend 3", 24.000), ("Bend 4", 30.000)],
        )
        self.height_axis = AxisState(
            name="Stop Height",
            min_limit=0.0,
            max_limit=150.0,
            presets=[("5/8 Die", 10.000), ("1.0 Die", 11.000), ("1.5 Die", 12.000), ("2.0 Die", 13.000)],
        )

        self.controller = self.build_controller()

        self.geometry(f"{SCREEN_WIDTH}x{SCREEN_HEIGHT}")
        self.minsize(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.grid_columnconfigure((0, 1, 2), weight=1, uniform="main")
        self.grid_rowconfigure(0, weight=1)

        self.left_panel = ctk.CTkFrame(self)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(PANEL_PADX, 10), pady=PANEL_PADY)
        self.left_panel.grid_columnconfigure(0, weight=1)
        self.left_panel.grid_rowconfigure(1, weight=1)

        self.calculator = CalculatorPanel(self.left_panel, self.send_calculator_to_depth, self.send_calculator_to_height)
        self.calculator.grid(row=0, column=0, sticky="new")

        self.schematic = BackgaugeSchematic(self.left_panel)
        self.schematic.grid(row=1, column=0, sticky="nsew", pady=(10, 0))

        self.depth_panel = AxisPanel(self, self.depth_axis, self.controller.depth, self.sync_schematic)
        self.depth_panel.grid(row=0, column=1, sticky="nsew", padx=10, pady=PANEL_PADY)

        self.height_panel = AxisPanel(self, self.height_axis, self.controller.height, self.sync_schematic)
        self.height_panel.grid(row=0, column=2, sticky="nsew", padx=(10, PANEL_PADX), pady=PANEL_PADY)

        bottom_frame = ctk.CTkFrame(self)
        bottom_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=PANEL_PADX, pady=(0, PANEL_PADY))
        bottom_frame.grid_columnconfigure(0, weight=1)

        self.home_panel = HomePanel(bottom_frame, self.home_all, self.home_depth, self.home_height)
        self.home_panel.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 6))

        self.status_label = ctk.CTkLabel(bottom_frame, text=f"{MODE} MODE  |  IDLE", anchor="w", font=STATUS_FONT)
        self.status_label.grid(row=1, column=0, sticky="ew", padx=14, pady=(2, 12))

        self.sync_from_controller()
        self.after(100, self.periodic_refresh)

    def periodic_refresh(self) -> None:
        self.sync_from_controller()
        self.after(100, self.periodic_refresh)

    def build_controller(self):
        depth_config = AxisConfig(
            name=self.depth_axis.name,
            min_limit=self.depth_axis.min_limit,
            max_limit=self.depth_axis.max_limit,
            jog_steps=self.depth_axis.jog_steps,
            presets=self.depth_axis.presets,
            home_position=self.depth_axis.min_limit,
            steps_per_unit=200.0,
            max_rpm=500.0,
            direction_pin=29,
            step_pin=11,
            min_sensor_pin=16,
            max_sensor_pin=22,
            cw_value=0,
            ccw_value=1,
            simulate_timing=False,
            timing_scale=1.0,
        )
        height_config = AxisConfig(
            name=self.height_axis.name,
            min_limit=self.height_axis.min_limit,
            max_limit=self.height_axis.max_limit,
            jog_steps=self.height_axis.jog_steps,
            presets=self.height_axis.presets,
            home_position=self.height_axis.min_limit,
            steps_per_unit=200.0,
            max_rpm=500.0,
            direction_pin=31,
            step_pin=13,
            min_sensor_pin=18,
            max_sensor_pin=24,
            cw_value=0,
            ccw_value=1,
            simulate_timing=False,
            timing_scale=1.0,
        )

        mode = MODE.upper().strip()
        if mode == "HW":
            controller = BackgaugeHardwareController(
                depth_config=depth_config,
                height_config=height_config,
                status_callback=self.set_status,
                state_callback=self.sync_from_controller,
            )
            controller.initialize_gpio()
            return controller

        return BackgaugeSimController(
            depth_config=depth_config,
            height_config=height_config,
            status_callback=self.set_status,
            state_callback=self.sync_from_controller,
        )

    def set_status(self, message: str) -> None:
        if hasattr(self, "status_label"):
            self.status_label.configure(text=f"{MODE} MODE  |  {message}")

    def sync_from_controller(self) -> None:
        if hasattr(self, "depth_panel"):
            self.depth_panel.refresh_from_controller()
        if hasattr(self, "height_panel"):
            self.height_panel.refresh_from_controller()
        if hasattr(self, "schematic"):
            self.sync_schematic()

    def sync_schematic(self) -> None:
        depth_state = self.controller.depth.state
        height_state = self.controller.height.state
        self.schematic.set_values(
            depth_state.current,
            depth_state.commanded,
            height_state.current,
            height_state.commanded,
            depth_state.in_position and height_state.in_position,
        )

    def send_calculator_to_depth(self, value: float) -> None:
        self.controller.depth.set_commanded(value)
        self.sync_from_controller()

    def send_calculator_to_height(self, value: float) -> None:
        self.controller.height.set_commanded(value)
        self.sync_from_controller()

    def home_depth(self) -> None:
        self.controller.depth.home()
        self.sync_from_controller()

    def home_height(self) -> None:
        self.controller.height.home()
        self.sync_from_controller()

    def home_all(self) -> None:
        self.controller.home_all()
        self.sync_from_controller()
        self.set_status("All axes homed")


if __name__ == "__main__":
    app = BackgaugeApp()
    app.mainloop()
