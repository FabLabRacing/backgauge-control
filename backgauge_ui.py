import customtkinter as ctk
from dataclasses import dataclass, field
import configparser
from tkinter import messagebox
import os
import shutil
import tempfile
import hashlib
from typing import Callable, Any
import ast
from backgauge_common import AxisConfig
from backgauge_controller import BackgaugeHardwareController


SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
CONF_SCREEN_WIDTH = 800
CONF_SCREEN_HEIGHT = 600
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


CONFIG_FILE = "backgauge.ini"
SECURITY_SECTION = "security"
PASSWORD_KEY = "machine_setup_password"
BACKUP_SUFFIX = ".bak"

PROTECTED_SECTIONS = [
    "ui",
    "depth_motion",
    "height_motion",
    "depth_pins",
    "height_pins",
    "security",
]

PRESET_SECTIONS = [
    "depth_presets",
    "height_presets",
]


def make_preset_label(key: str) -> str:
    return key.replace("_", " ").title()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def get_password_from_ini(path=CONFIG_FILE) -> str:
    config = configparser.ConfigParser()
    config.read(path)
    return config.get(SECURITY_SECTION, PASSWORD_KEY, fallback="")


def set_password_in_ini(new_password: str, config_path=CONFIG_FILE) -> None:
    config = configparser.ConfigParser()
    config.read(config_path)
    if SECURITY_SECTION not in config:
        config[SECURITY_SECTION] = {}
    config[SECURITY_SECTION][PASSWORD_KEY] = hash_password(new_password)
    config_dir = os.path.dirname(os.path.abspath(config_path)) or "."
    with tempfile.NamedTemporaryFile("w", delete=False, dir=config_dir) as tf:
        config.write(tf)
        tempname = tf.name
    os.replace(tempname, config_path)


def backup_ini(path: str) -> str:
    backup_file = path + BACKUP_SUFFIX
    shutil.copy2(path, backup_file)
    return backup_file


@dataclass
class AxisState:
    name: str
    current: float = 0.0
    commanded: str = "0.000"
    min_limit: float = 0.0
    max_limit: float = 240.0
    jog_steps: tuple[float, float, float] = (0.100, 0.010, 0.001)
    presets: list[tuple[str, float]] = field(default_factory=list)


def safe_eval(expr: str) -> float:
    """Safely evaluate a math expression using ast. Only allows +, -, *, /, (), and numbers."""
    allowed_nodes = {
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Num,
        ast.Constant,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.UAdd,
        ast.USub,
    }

    def _eval(node):
        if type(node) not in allowed_nodes:
            raise ValueError(f"Disallowed expression: {type(node).__name__}")
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        elif isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            elif isinstance(node.op, ast.Sub):
                return left - right
            elif isinstance(node.op, ast.Mult):
                return left * right
            elif isinstance(node.op, ast.Div):
                return left / right
            else:
                raise ValueError("Unsupported binary operator")
        elif isinstance(node, ast.UnaryOp):
            operand = _eval(node.operand)
            if isinstance(node.op, ast.UAdd):
                return +operand
            elif isinstance(node.op, ast.USub):
                return -operand
            else:
                raise ValueError("Unsupported unary operator")
        elif isinstance(node, ast.Num):  # Python <3.8
            return node.n
        elif isinstance(node, ast.Constant):  # Python 3.8+
            if isinstance(node.value, (int, float)):
                return node.value
            else:
                raise ValueError("Only int and float constants allowed")
        else:
            raise ValueError(f"Disallowed node: {type(node).__name__}")

    try:
        parsed = ast.parse(expr, mode="eval")
        return float(_eval(parsed))
    except Exception as e:
        raise ValueError(f"Invalid expression: {e}")

class CalculatorPanel(ctk.CTkFrame):
    def __init__(self, master: Any, on_send_depth: Callable[[float], None], on_send_height: Callable[[float], None]) -> None:
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
            result = safe_eval(expression)
            self.set_value(result)
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
    def __init__(self, master: Any) -> None:
        super().__init__(master)
        self.depth_current = 0.0
        self.depth_commanded = 0.0
        self.height_current = 0.0
        self.height_commanded = 0.0
        self.depth_max = 40.0
        self.height_max = 15.0
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

    def set_values(
        self,
        depth_current: float,
        depth_commanded: float,
        height_current: float,
        height_commanded: float,
        in_position: bool,
    ) -> None:
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

    def redraw(self) -> None:
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
    def __init__(self, master: Any, axis: AxisState, controller_axis, change_callback: Callable[[], None] | None = None) -> None:
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

        fine_jog_frame = ctk.CTkFrame(self)
        fine_jog_frame.grid(row=7, column=0, columnspan=3, sticky="ew", padx=12, pady=(8, 8))
        fine_jog_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

        fine_jog_buttons = [
            ("-.001", -0.001),
            ("-.010", -0.010),
            ("-.100", -0.100),
            ("+.001", 0.001),
            ("+.010", 0.010),
            ("+.100", 0.100),
        ]

        for col, (label, delta) in enumerate(fine_jog_buttons):
            ctk.CTkButton(
                fine_jog_frame,
                text=label,
                height=SMALL_BUTTON_HEIGHT,
                command=lambda d=delta: self.nudge(d),
            ).grid(row=0, column=col, sticky="ew", padx=4, pady=6)

        jog_frame = ctk.CTkFrame(self)
        jog_frame.grid(row=6, column=0, columnspan=3, sticky="ew", padx=12, pady=(12, 8))
        jog_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(jog_frame, text="Jog", font=SECTION_FONT).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(8, 4))
        ctk.CTkLabel(
            jog_frame,
            text="Press and hold to jog",
            font=("Arial", 14),
            anchor="e",
        ).grid(row=0, column=1, sticky="e", padx=10, pady=(8, 4))

        self.jog_minus_button = ctk.CTkButton(jog_frame, text="JOG -", height=BUTTON_HEIGHT, font=BUTTON_FONT)
        self.jog_minus_button.grid(row=1, column=0, sticky="ew", padx=(6, 6), pady=(6, 10))
        self.jog_plus_button = ctk.CTkButton(jog_frame, text="JOG +", height=BUTTON_HEIGHT, font=BUTTON_FONT)
        self.jog_plus_button.grid(row=1, column=1, sticky="ew", padx=(6, 6), pady=(6, 10))

        self.bind_jog_button(self.jog_minus_button, -1)
        self.bind_jog_button(self.jog_plus_button, 1)

        self.preset_frame = ctk.CTkFrame(self)
        self.preset_frame.grid(row=8, column=0, columnspan=3, sticky="ew", padx=12, pady=(8, 12))
        self.preset_frame.grid_columnconfigure((0, 1), weight=1)
        self.rebuild_preset_buttons()

        self.refresh_from_controller()

    @staticmethod
    def format_value(value: float) -> str:
        return f"{value:.3f}"

    def rebuild_preset_buttons(self) -> None:
        for child in self.preset_frame.winfo_children():
            child.destroy()

        self.preset_frame.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(
            self.preset_frame,
            text="Presets",
            font=SECTION_FONT,
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(8, 6))

        for idx, (label, value) in enumerate(self.axis.presets):
            ctk.CTkButton(
                self.preset_frame,
                text=label,
                height=SMALL_BUTTON_HEIGHT,
                command=lambda v=value: self.set_commanded(v),
            ).grid(row=1 + idx // 2, column=idx % 2, sticky="ew", padx=6, pady=6)

    def update_presets(self, presets: list[tuple[str, float]]) -> None:
        self.axis.presets = presets
        self.rebuild_preset_buttons()


    def refresh_from_controller(self) -> None:
        state = self.controller_axis.state
        self.current_label.configure(text=self.format_value(state.current))
        self.commanded_entry.delete(0, "end")
        self.commanded_entry.insert(0, self.format_value(state.commanded))
        self.update_colors()

    def update_colors(self) -> None:
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

    def bind_jog_button(self, button, direction: int) -> None:
        button.bind("<ButtonPress-1>", lambda event, d=direction: self.start_jog(d))
        button.bind("<ButtonRelease-1>", self.stop_jog)
        button.bind("<Leave>", self.stop_jog)

    def start_jog(self, direction: int) -> None:
        self.controller_axis.start_jog(direction)
        self.refresh_from_controller()
        if self.change_callback:
            self.change_callback()

    def stop_jog(self, event=None) -> None:
        self.controller_axis.stop_jog()
        self.refresh_from_controller()
        if self.change_callback:
            self.change_callback()

    def nudge(self, delta: float) -> None:
        if self.controller_axis.state.is_moving:
            return

        new_target = self.controller_axis.state.current + delta
        self.controller_axis.set_commanded(new_target)
        self.controller_axis.move_to_commanded()
        self.refresh_from_controller()
        if self.change_callback:
            self.change_callback()


class HomePanel(ctk.CTkFrame):
    def __init__(self, master: Any, home_all: Callable[[], None], home_depth: Callable[[], None], home_height: Callable[[], None]) -> None:
        super().__init__(master)
        self.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(self, text="Home All", height=BUTTON_HEIGHT, command=home_all).grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        ctk.CTkButton(self, text="Home Depth", height=BUTTON_HEIGHT, command=home_depth).grid(row=0, column=1, sticky="ew", padx=8, pady=8)
        ctk.CTkButton(self, text="Home Height", height=BUTTON_HEIGHT, command=home_height).grid(row=0, column=2, sticky="ew", padx=8, pady=8)


class PasswordDialog(ctk.CTkToplevel):
    def __init__(self, master: Any, title: str = "Password Required") -> None:
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.result = None
        ctk.CTkLabel(self, text="Enter password:", font=LABEL_FONT).grid(row=0, column=0, padx=18, pady=18)
        self.pw_var = ctk.StringVar()
        self.entry = ctk.CTkEntry(self, textvariable=self.pw_var, show="*", font=ENTRY_FONT, width=200)
        self.entry.grid(row=0, column=1, padx=18, pady=18)
        self.entry.focus()
        btn = ctk.CTkButton(self, text="OK", font=BUTTON_FONT, command=self.on_ok, height=BUTTON_HEIGHT)
        btn.grid(row=1, column=0, columnspan=2, pady=(0, 18))
        self.bind("<Return>", lambda e: self.on_ok())
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def on_ok(self) -> None:
        self.result = self.pw_var.get()
        self.destroy()


class ChangePasswordDialog(ctk.CTkToplevel):
    def __init__(self, master: Any, title: str = "Change Password") -> None:
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.result = None
        ctk.CTkLabel(self, text="Current password:", font=LABEL_FONT).grid(row=0, column=0, padx=18, pady=8)
        ctk.CTkLabel(self, text="New password:", font=LABEL_FONT).grid(row=1, column=0, padx=18, pady=8)
        ctk.CTkLabel(self, text="Confirm new password:", font=LABEL_FONT).grid(row=2, column=0, padx=18, pady=8)
        self.old_pw = ctk.CTkEntry(self, show="*", font=ENTRY_FONT)
        self.new_pw = ctk.CTkEntry(self, show="*", font=ENTRY_FONT)
        self.conf_pw = ctk.CTkEntry(self, show="*", font=ENTRY_FONT)
        self.old_pw.grid(row=0, column=1, padx=18, pady=8)
        self.new_pw.grid(row=1, column=1, padx=18, pady=8)
        self.conf_pw.grid(row=2, column=1, padx=18, pady=8)
        btn = ctk.CTkButton(self, text="OK", font=BUTTON_FONT, command=self.on_ok, height=BUTTON_HEIGHT)
        btn.grid(row=3, column=0, columnspan=2, pady=(0, 18))
        self.bind("<Return>", lambda e: self.on_ok())
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def on_ok(self) -> None:
        self.result = (
            self.old_pw.get(),
            self.new_pw.get(),
            self.conf_pw.get()
        )
        self.destroy()


class ConfigEditor(ctk.CTkToplevel):
    def __init__(self, master: Any, config_file: str, allowed_sections: list[str] = None, allow_password_change: bool = True, close_on_save: bool = False) -> None:
        super().__init__(master)
        self.title("Configuration Editor")
        self.geometry(f"{CONF_SCREEN_WIDTH}x{CONF_SCREEN_HEIGHT}")
        self.config_file = config_file
        self.allowed_sections = allowed_sections
        self.allow_password_change = allow_password_change
        self.close_on_save = close_on_save
        self.config = configparser.ConfigParser()
        self.fields = {}
        self.create_widgets()
        self.load_config()

    def create_widgets(self) -> None:
        self.notebook = ctk.CTkTabview(
            self,
            width=CONF_SCREEN_WIDTH - 2 * PANEL_PADX,
            height=CONF_SCREEN_HEIGHT - 120,
        )
        self.notebook.pack(fill="both", expand=True, padx=PANEL_PADX, pady=(PANEL_PADY, 0))

        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.pack(fill="x", padx=PANEL_PADX, pady=(10, PANEL_PADY))

        ctk.CTkButton(
            self.button_frame,
            text="Save",
            command=self.save_config,
            font=BUTTON_FONT,
            height=BUTTON_HEIGHT,
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            self.button_frame,
            text="Cancel",
            command=self.destroy,
            font=BUTTON_FONT,
            height=BUTTON_HEIGHT,
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            self.button_frame,
            text="Reload from file",
            command=self.load_config,
            font=BUTTON_FONT,
            height=BUTTON_HEIGHT,
        ).pack(side="left", padx=8)

        if self.allow_password_change:
            ctk.CTkButton(
                self.button_frame,
                text="Change Password",
                command=self.change_password,
                font=BUTTON_FONT,
                height=BUTTON_HEIGHT,
            ).pack(side="right", padx=8)

    def load_config(self) -> None:
        self.config.read(self.config_file)

        if hasattr(self.notebook, "tabs"):
            for tab_name in self.notebook.tabs():
                self.notebook.delete(tab_name)
        else:
            for tab_name in list(self.notebook._tab_dict.keys()):
                self.notebook.delete(tab_name)

        self.fields.clear()

        for section in self.config.sections():
            if self.allowed_sections is not None and section not in self.allowed_sections:
                continue

            self.notebook.add(section)
            tab_frame = self.notebook.tab(section)
            tab_frame.grid_columnconfigure(1, weight=1)
            self.fields[section] = {}
            row = 0

            for key, value in self.config[section].items():
                if section == SECURITY_SECTION and key == PASSWORD_KEY:
                    continue

                ctk.CTkLabel(tab_frame, text=key, font=LABEL_FONT).grid(
                    row=row, column=0, sticky="w", padx=12, pady=6
                )
                entry = ctk.CTkEntry(tab_frame, font=ENTRY_FONT, width=220)
                entry.insert(0, value)
                entry.grid(row=row, column=1, sticky="ew", padx=12, pady=6)
                self.fields[section][key] = entry
                row += 1

    def save_config(self) -> None:
        key_types = {
            "min_limit": float,
            "max_limit": float,
            "home_position": float,
            "steps_per_unit": float,
            "max_rpm": float,
            "cw_value": int,
            "ccw_value": int,
            "simulate_timing": bool,
            "timing_scale": float,
            "jog_step_1": float,
            "jog_step_2": float,
            "jog_step_3": float,
            "step_pin": int,
            "direction_pin": int,
            "min_sensor_pin": int,
            "max_sensor_pin": int,
            "fullscreen": bool,
            "update_interval_ms": int,
            "show_backgauge_view": bool,
        }

        for section, keys in self.fields.items():
            for key, entry in keys.items():
                value = entry.get()
                expected_type = key_types.get(key)

                if expected_type is bool:
                    if value.lower() not in ["true", "false"]:
                        messagebox.showerror("Validation Error", f"{section}.{key} must be 'true' or 'false'")
                        return
                elif expected_type is int:
                    try:
                        int(value)
                    except ValueError:
                        messagebox.showerror("Validation Error", f"{section}.{key} must be an integer")
                        return
                elif expected_type is float:
                    try:
                        float(value)
                    except ValueError:
                        messagebox.showerror("Validation Error", f"{section}.{key} must be a float")
                        return

                self.config[section][key] = value

        try:
            backup_file = backup_ini(self.config_file)
            config_dir = os.path.dirname(os.path.abspath(self.config_file)) or "."
            with tempfile.NamedTemporaryFile("w", delete=False, dir=config_dir) as tf:
                self.config.write(tf)
                tempname = tf.name
            os.replace(tempname, self.config_file)
            messagebox.showinfo("Success", f"Configuration saved.\nBackup: {backup_file}")
            if self.close_on_save:
                self.destroy()
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save config: {e}")

    def change_password(self) -> None:
        dlg = ChangePasswordDialog(self, title="Change Password")
        dlg.wait_visibility()
        dlg.grab_set()
        self.wait_window(dlg)

        if dlg.result:
            old_pw, new_pw, conf_pw = dlg.result
            current_hash = get_password_from_ini(self.config_file)

            if hash_password(old_pw) != current_hash:
                messagebox.showerror("Error", "Current password is incorrect.")
                return

            if not new_pw or new_pw != conf_pw:
                messagebox.showerror("Error", "New passwords do not match or are empty.")
                return

            try:
                if SECURITY_SECTION not in self.config:
                    self.config[SECURITY_SECTION] = {}
                self.config[SECURITY_SECTION][PASSWORD_KEY] = hash_password(new_pw)
                self.save_config()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to change password: {e}")


class BackgaugeApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.config_data = self.load_ini()
        self.fullscreen = self.get_config_bool("ui", "fullscreen", True)
        self.update_interval_ms = self.get_config_int("ui", "update_interval_ms", 100)
        self.show_backgauge_view = self.get_config_bool("ui", "show_backgauge_view", True)
        self._sync_pending = False

        self.title("Backgauge Control")
        self.attributes("-fullscreen", self.fullscreen)
        self.create_gear_icon()
        self.bind("<Escape>", lambda event: self.destroy())

        self.depth_axis = AxisState(
            name="Stop Depth",
            min_limit=0.0,
            max_limit=240.0,
            presets=self.load_presets(
                "depth_presets",
                [("Bend 1", 12.000), ("Bend 2", 18.500), ("Bend 3", 24.000), ("Bend 4", 30.000)],
            ),
        )
        self.height_axis = AxisState(
            name="Stop Height",
            min_limit=0.0,
            max_limit=150.0,
            presets=self.load_presets(
                "height_presets",
                [("5/8 Die", 10.000), ("1.0 Die", 11.000), ("1.5 Die", 12.000), ("2.0 Die", 13.000)],
            ),
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

        self.schematic = None
        if self.show_backgauge_view:
            self.schematic = BackgaugeSchematic(self.left_panel)
            self.schematic.grid(row=1, column=0, sticky="nsew", pady=(10, 0))

        self.depth_panel = AxisPanel(self, self.depth_axis, self.controller.depth, self.sync_schematic)
        self.depth_panel.grid(row=0, column=1, sticky="nsew", padx=10, pady=PANEL_PADY)

        self.height_panel = AxisPanel(self, self.height_axis, self.controller.height, self.sync_schematic)
        self.height_panel.grid(row=0, column=2, sticky="nsew", padx=(10, PANEL_PADX), pady=PANEL_PADY)

        bottom_frame = ctk.CTkFrame(self)
        bottom_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=PANEL_PADX, pady=(0, PANEL_PADY))
        bottom_frame.grid_columnconfigure((0, 1), weight=1)

        self.home_panel = HomePanel(bottom_frame, self.home_all, self.home_depth, self.home_height)
        self.home_panel.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 6))

        self.presets_button = ctk.CTkButton(
            bottom_frame,
            text="Edit Presets",
            height=BUTTON_HEIGHT,
            font=BUTTON_FONT,
            command=self.open_presets_editor,
        )
        self.presets_button.grid(row=0, column=1, sticky="ew", padx=8, pady=(8, 6))

        self.status_label = ctk.CTkLabel(bottom_frame, text="IDLE", anchor="w", font=STATUS_FONT)
        self.status_label.grid(row=1, column=0, columnspan=2, sticky="ew", padx=14, pady=(2, 12))

        self.sync_from_controller()
        self.after(self.update_interval_ms, self.periodic_refresh)

    def periodic_refresh(self) -> None:
        self.sync_from_controller()
        self.after(self.update_interval_ms, self.periodic_refresh)

    def get_config_float(self, section: str, option: str, fallback: float) -> float:
        try:
            return self.config_data.getfloat(section, option, fallback=fallback)
        except Exception:
            return fallback

    def get_config_int(self, section: str, option: str, fallback: int) -> int:
        try:
            return self.config_data.getint(section, option, fallback=fallback)
        except Exception:
            return fallback

    def get_config_bool(self, section: str, option: str, fallback: bool) -> bool:
        try:
            return self.config_data.getboolean(section, option, fallback=fallback)
        except Exception:
            return fallback

    def get_config_jog_steps(self, section: str, fallback: tuple[float, float, float]) -> tuple[float, float, float]:
        try:
            js1 = self.get_config_float(section, "jog_step_1", fallback[0])
            js2 = self.get_config_float(section, "jog_step_2", fallback[1])
            js3 = self.get_config_float(section, "jog_step_3", fallback[2])
            return (js1, js2, js3)
        except Exception:
            return fallback

    def get_config_pin(self, section: str, option: str, fallback: int) -> int:
        try:
            return self.config_data.getint(section, option, fallback=fallback)
        except Exception:
            return fallback

    def build_controller(self):
        depth_section = "depth_motion"
        depth_pins_section = "depth_pins"
        depth_min_limit = self.get_config_float(depth_section, "min_limit", 0.0)
        depth_max_limit = self.get_config_float(depth_section, "max_limit", 240.0)
        depth_home_position = self.get_config_float(depth_section, "home_position", depth_min_limit)
        depth_steps_per_unit = self.get_config_float(depth_section, "steps_per_unit", 200.0)
        depth_max_rpm = self.get_config_float(depth_section, "max_rpm", 500.0)
        depth_cw_value = self.get_config_int(depth_section, "cw_value", 0)
        depth_ccw_value = self.get_config_int(depth_section, "ccw_value", 1)
        depth_simulate_timing = self.get_config_bool(depth_section, "simulate_timing", False)
        depth_timing_scale = self.get_config_float(depth_section, "timing_scale", 1.0)
        depth_jog_steps = self.get_config_jog_steps(depth_section, (0.100, 0.010, 0.001))
        depth_direction_pin = self.get_config_pin(depth_pins_section, "direction_pin", 29)
        depth_step_pin = self.get_config_pin(depth_pins_section, "step_pin", 11)
        depth_min_sensor_pin = self.get_config_pin(depth_pins_section, "min_sensor_pin", 16)
        depth_max_sensor_pin = self.get_config_pin(depth_pins_section, "max_sensor_pin", 22)

        height_section = "height_motion"
        height_pins_section = "height_pins"
        height_min_limit = self.get_config_float(height_section, "min_limit", 0.0)
        height_max_limit = self.get_config_float(height_section, "max_limit", 150.0)
        height_home_position = self.get_config_float(height_section, "home_position", height_min_limit)
        height_steps_per_unit = self.get_config_float(height_section, "steps_per_unit", 200.0)
        height_max_rpm = self.get_config_float(height_section, "max_rpm", 500.0)
        height_cw_value = self.get_config_int(height_section, "cw_value", 0)
        height_ccw_value = self.get_config_int(height_section, "ccw_value", 1)
        height_simulate_timing = self.get_config_bool(height_section, "simulate_timing", False)
        height_timing_scale = self.get_config_float(height_section, "timing_scale", 1.0)
        height_jog_steps = self.get_config_jog_steps(height_section, (0.100, 0.010, 0.001))
        height_direction_pin = self.get_config_pin(height_pins_section, "direction_pin", 31)
        height_step_pin = self.get_config_pin(height_pins_section, "step_pin", 13)
        height_min_sensor_pin = self.get_config_pin(height_pins_section, "min_sensor_pin", 18)
        height_max_sensor_pin = self.get_config_pin(height_pins_section, "max_sensor_pin", 24)

        depth_config = AxisConfig(
            name=self.depth_axis.name,
            min_limit=depth_min_limit,
            max_limit=depth_max_limit,
            jog_steps=depth_jog_steps,
            presets=self.depth_axis.presets,
            home_position=depth_home_position,
            steps_per_unit=depth_steps_per_unit,
            max_rpm=depth_max_rpm,
            direction_pin=depth_direction_pin,
            step_pin=depth_step_pin,
            min_sensor_pin=depth_min_sensor_pin,
            max_sensor_pin=depth_max_sensor_pin,
            cw_value=depth_cw_value,
            ccw_value=depth_ccw_value,
            simulate_timing=depth_simulate_timing,
            timing_scale=depth_timing_scale,
        )

        height_config = AxisConfig(
            name=self.height_axis.name,
            min_limit=height_min_limit,
            max_limit=height_max_limit,
            jog_steps=height_jog_steps,
            presets=self.height_axis.presets,
            home_position=height_home_position,
            steps_per_unit=height_steps_per_unit,
            max_rpm=height_max_rpm,
            direction_pin=height_direction_pin,
            step_pin=height_step_pin,
            min_sensor_pin=height_min_sensor_pin,
            max_sensor_pin=height_max_sensor_pin,
            cw_value=height_cw_value,
            ccw_value=height_ccw_value,
            simulate_timing=height_simulate_timing,
            timing_scale=height_timing_scale,
        )

        mode = self.get_config_value("ui", "mode", "pi_gpio").strip().lower()

        if mode == "esp32":
            from backgauge_esp32_controller import BackgaugeESP32Controller

            esp32_port = self.get_config_value("ui", "esp32_port", "/dev/ttyUSB0")
            esp32_baud = self.get_config_int("ui", "esp32_baud", 115200)

            controller = BackgaugeESP32Controller(
                depth_config=depth_config,
                height_config=height_config,
                port=esp32_port,
                baudrate=esp32_baud,
                status_callback=self.threadsafe_status,
                state_callback=self.request_sync,
            )
        else:
            controller = BackgaugeHardwareController(
                depth_config=depth_config,
                height_config=height_config,
                status_callback=self.threadsafe_status,
                state_callback=self.request_sync,
            )

        controller.initialize_gpio()
        return controller

    def load_ini(self) -> configparser.ConfigParser:
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE)
        return config

    def get_config_value(self, section: str, option: str, fallback: str) -> str:
        try:
            return self.config_data.get(section, option, fallback=fallback)
        except Exception:
            return fallback

    def load_presets(self, section: str, fallback: list[tuple[str, float]]) -> list[tuple[str, float]]:
        if not self.config_data.has_section(section):
            return fallback

        presets: list[tuple[str, float]] = []
        for key, value in self.config_data.items(section):
            try:
                presets.append((make_preset_label(key), float(value)))
            except ValueError:
                continue

        return presets or fallback

    def threadsafe_status(self, message: str) -> None:
        self.after(0, lambda m=message: self.set_status(m))

    def request_sync(self) -> None:
        if self._sync_pending:
            return
        self._sync_pending = True
        self.after(0, self._run_sync)

    def _run_sync(self) -> None:
        self._sync_pending = False
        self.sync_from_controller()

    def set_status(self, message: str) -> None:
        if hasattr(self, "status_label"):
            self.status_label.configure(text=message)

    def sync_from_controller(self) -> None:
        if hasattr(self, "depth_panel"):
            self.depth_panel.refresh_from_controller()
        if hasattr(self, "height_panel"):
            self.height_panel.refresh_from_controller()
        if getattr(self, "schematic", None) is not None:
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

    def open_presets_editor(self) -> None:
        editor = ConfigEditor(
            self,
            CONFIG_FILE,
            allowed_sections=PRESET_SECTIONS,
            allow_password_change=False,
            close_on_save=True,
        )
        self.wait_window(editor)

        self.config_data = self.load_ini()

        depth_presets = self.load_presets(
            "depth_presets",
            [("Bend 1", 12.000), ("Bend 2", 18.500), ("Bend 3", 24.000), ("Bend 4", 30.000)],
        )
        height_presets = self.load_presets(
            "height_presets",
            [("5/8 Die", 10.000), ("1.0 Die", 11.000), ("1.5 Die", 12.000), ("2.0 Die", 13.000)],
        )

        self.depth_axis.presets = depth_presets
        self.height_axis.presets = height_presets

        self.controller.depth.config.presets = depth_presets
        self.controller.height.config.presets = height_presets

        self.depth_panel.update_presets(depth_presets)
        self.height_panel.update_presets(height_presets)

        self.sync_from_controller()

    def destroy(self) -> None:
        if hasattr(self, "controller"):
            if hasattr(self.controller.depth, "stop_jog"):
                self.controller.depth.stop_jog()
            if hasattr(self.controller.height, "stop_jog"):
                self.controller.height.stop_jog()
            if hasattr(self.controller, "shutdown_gpio"):
                self.controller.shutdown_gpio()
        super().destroy()

    def create_gear_icon(self) -> None:
        gear_btn = ctk.CTkButton(self, text="⚙️", font=BUTTON_FONT, width=30, height=30, command=self.open_password_dialog)
        gear_btn.place(relx=1.0, rely=1.0, anchor="se", x=-10, y=-10)

    def open_password_dialog(self) -> None:
        dlg = PasswordDialog(self, title="Password Required")
        dlg.wait_visibility()
        dlg.grab_set()
        self.wait_window(dlg)
        pw = dlg.result
        if pw is None:
            return

        correct_hash = get_password_from_ini()
        if hash_password(pw) == correct_hash:
            ConfigEditor(
                self,
                CONFIG_FILE,
                allowed_sections=PROTECTED_SECTIONS,
                allow_password_change=True,
            )
        else:
            messagebox.showerror("Access Denied", "Incorrect password.")


if __name__ == "__main__":
    app = BackgaugeApp()
    app.mainloop()