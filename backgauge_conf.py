import customtkinter as ctk
from tkinter import messagebox, simpledialog
import configparser
import os
import shutil

CONFIG_FILE = "backgauge.ini"
SECURITY_SECTION = "security"
PASSWORD_KEY = "machine_setup_password"
BACKUP_SUFFIX = ".bak"

# UI constants from backgauge_ui.py
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
PANEL_PADX = 18
PANEL_PADY = 18
TITLE_FONT = ("Arial", 34, "bold")
SECTION_FONT = ("Arial", 20, "bold")
LABEL_FONT = ("Arial", 18)
ENTRY_FONT = ("Arial", 20)
BUTTON_FONT = ("Arial", 20, "bold")
STATUS_FONT = ("Arial", 16, "bold")
BUTTON_HEIGHT = 48
SMALL_BUTTON_HEIGHT = 40

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

def get_password_from_ini():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    return config.get(SECURITY_SECTION, PASSWORD_KEY, fallback="")

def set_password_in_ini(new_password):
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    if SECURITY_SECTION not in config:
        config[SECURITY_SECTION] = {}
    config[SECURITY_SECTION][PASSWORD_KEY] = new_password
    with open(CONFIG_FILE, "w") as f:
        config.write(f)

def backup_ini():
    backup_file = CONFIG_FILE + BACKUP_SUFFIX
    shutil.copy2(CONFIG_FILE, backup_file)
    return backup_file


class PasswordDialog(ctk.CTkToplevel):

    def __init__(self, master, title="Password Required"):
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

    def on_ok(self):
        self.result = self.pw_var.get()
        self.destroy()


class ChangePasswordDialog(ctk.CTkToplevel):
    def __init__(self, master, title="Change Password"):
        super().__init__(master)
        self.title(title)
        self.grab_set()
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
        self.wait_window(self)

    def on_ok(self):
        self.result = (
            self.old_pw.get(),
            self.new_pw.get(),
            self.conf_pw.get()
        )
        self.destroy()



# --- BEGIN REPLACEMENT ---
import customtkinter as ctk
from tkinter import messagebox
import configparser
import os
import shutil
import tempfile
import hashlib

CONFIG_FILE = "backgauge.ini"
SECURITY_SECTION = "security"
PASSWORD_KEY = "machine_setup_password"
BACKUP_SUFFIX = ".bak"

# UI constants from backgauge_ui.py
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
PANEL_PADX = 18
PANEL_PADY = 18
TITLE_FONT = ("Arial", 34, "bold")
SECTION_FONT = ("Arial", 20, "bold")
LABEL_FONT = ("Arial", 18)
ENTRY_FONT = ("Arial", 20)
BUTTON_FONT = ("Arial", 20, "bold")
STATUS_FONT = ("Arial", 16, "bold")
BUTTON_HEIGHT = 48
SMALL_BUTTON_HEIGHT = 40

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def get_password_from_ini(path=CONFIG_FILE):
    config = configparser.ConfigParser()
    config.read(path)
    return config.get(SECURITY_SECTION, PASSWORD_KEY, fallback="")

def set_password_in_ini(new_password, config_path=CONFIG_FILE):
    config = configparser.ConfigParser()
    config.read(config_path)
    if SECURITY_SECTION not in config:
        config[SECURITY_SECTION] = {}
    config[SECURITY_SECTION][PASSWORD_KEY] = hash_password(new_password)
    with tempfile.NamedTemporaryFile('w', delete=False) as tf:
        config.write(tf)
        tempname = tf.name
    os.replace(tempname, config_path)

def backup_ini(path):
    backup_file = path + BACKUP_SUFFIX
    shutil.copy2(path, backup_file)
    return backup_file

class PasswordDialog(ctk.CTkToplevel):
    def __init__(self, master, title="Password Required"):
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

    def on_ok(self):
        self.result = self.pw_var.get()
        self.destroy()

class ChangePasswordDialog(ctk.CTkToplevel):
    def __init__(self, master, title="Change Password"):
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

    def on_ok(self):
        self.result = (
            self.old_pw.get(),
            self.new_pw.get(),
            self.conf_pw.get()
        )
        self.destroy()

class ConfigEditor(ctk.CTkToplevel):
    def __init__(self, master, config_file):
        super().__init__(master)
        self.title("Configuration Editor")
        self.geometry(f"{SCREEN_WIDTH}x{SCREEN_HEIGHT}")
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.fields = {}
        self.create_widgets()
        self.load_config()

    def create_widgets(self):
        self.notebook = ctk.CTkTabview(self, width=SCREEN_WIDTH-2*PANEL_PADX, height=SCREEN_HEIGHT-120)
        self.notebook.pack(fill="both", expand=True, padx=PANEL_PADX, pady=(PANEL_PADY, 0))
        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.pack(fill="x", padx=PANEL_PADX, pady=(10, PANEL_PADY))
        ctk.CTkButton(self.button_frame, text="Save", command=self.save_config, font=BUTTON_FONT, height=BUTTON_HEIGHT).pack(side="left", padx=8)
        ctk.CTkButton(self.button_frame, text="Cancel", command=self.destroy, font=BUTTON_FONT, height=BUTTON_HEIGHT).pack(side="left", padx=8)
        ctk.CTkButton(self.button_frame, text="Reload from file", command=self.load_config, font=BUTTON_FONT, height=BUTTON_HEIGHT).pack(side="left", padx=8)
        ctk.CTkButton(self.button_frame, text="Change Password", command=self.change_password, font=BUTTON_FONT, height=BUTTON_HEIGHT).pack(side="right", padx=8)

    def load_config(self):
        self.config.read(self.config_file)
        # Remove all tabs from the tabview using public API if available
        if hasattr(self.notebook, 'tabs'):
            for tab_name in self.notebook.tabs():
                self.notebook.delete(tab_name)
        else:
            for tab_name in list(self.notebook._tab_dict.keys()):
                self.notebook.delete(tab_name)
        self.fields.clear()
        for section in self.config.sections():
            self.notebook.add(section)
            tab_frame = self.notebook.tab(section)
            tab_frame.grid_columnconfigure(1, weight=1)
            self.fields[section] = {}
            row = 0
            for key, value in self.config[section].items():
                ctk.CTkLabel(tab_frame, text=key, font=LABEL_FONT).grid(row=row, column=0, sticky="w", padx=12, pady=6)
                entry = ctk.CTkEntry(tab_frame, font=ENTRY_FONT, width=220)
                entry.insert(0, value)
                entry.grid(row=row, column=1, sticky="ew", padx=12, pady=6)
                self.fields[section][key] = entry
                row += 1

    def save_config(self):
        key_types = {
            'min_limit': float, 'max_limit': float, 'home_position': float, 'steps_per_unit': float, 'max_rpm': float,
            'cw_value': int, 'ccw_value': int, 'simulate_timing': bool, 'timing_scale': float,
            'jog_step_1': float, 'jog_step_2': float, 'jog_step_3': float,
            'step_pin': int, 'direction_pin': int, 'min_sensor_pin': int, 'max_sensor_pin': int,
            'fullscreen': bool, 'update_interval_ms': int, 'show_backgauge_view': bool
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
            with tempfile.NamedTemporaryFile('w', delete=False) as tf:
                self.config.write(tf)
                tempname = tf.name
            os.replace(tempname, self.config_file)
            messagebox.showinfo("Success", f"Configuration saved.\nBackup: {backup_file}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save config: {e}")

    def change_password(self):
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
                if SECURITY_SECTION in self.fields and PASSWORD_KEY in self.fields[SECURITY_SECTION]:
                    self.fields[SECURITY_SECTION][PASSWORD_KEY].delete(0, 'end')
                    self.fields[SECURITY_SECTION][PASSWORD_KEY].insert(0, hash_password(new_pw))
                self.save_config()
                messagebox.showinfo("Success", "Password changed successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to change password: {e}")

class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Backgauge Config Test")
        self.geometry("400x300")
        self.create_gear_icon()

    def create_gear_icon(self):
        gear_btn = ctk.CTkButton(self, text="⚙️", font=BUTTON_FONT, width=60, height=60, command=self.open_password_dialog)
        gear_btn.place(relx=1.0, rely=1.0, anchor="se", x=-10, y=-10)

    def open_password_dialog(self):
        dlg = PasswordDialog(self, title="Password Required")
        dlg.wait_visibility()
        dlg.grab_set()
        self.wait_window(dlg)
        pw = dlg.result
        if pw is None:
            return
        correct_hash = get_password_from_ini()
        if hash_password(pw) == correct_hash:
            ConfigEditor(self, CONFIG_FILE)
        else:
            messagebox.showerror("Access Denied", "Incorrect password.")

if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
# --- END REPLACEMENT ---