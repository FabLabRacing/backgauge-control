import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import configparser
import os
import shutil

CONFIG_FILE = "backgauge.ini"
SECURITY_SECTION = "security"
PASSWORD_KEY = "machine_setup_password"
BACKUP_SUFFIX = ".bak"

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

class PasswordDialog(simpledialog.Dialog):
    def body(self, master):
        tk.Label(master, text="Enter password:").grid(row=0, column=0, padx=8, pady=8)
        self.pw_var = tk.StringVar()
        self.entry = tk.Entry(master, textvariable=self.pw_var, show="*")
        self.entry.grid(row=0, column=1, padx=8, pady=8)
        return self.entry

    def apply(self):
        self.result = self.pw_var.get()

class ChangePasswordDialog(simpledialog.Dialog):
    def body(self, master):
        tk.Label(master, text="Current password:").grid(row=0, column=0, padx=8, pady=4)
        tk.Label(master, text="New password:").grid(row=1, column=0, padx=8, pady=4)
        tk.Label(master, text="Confirm new password:").grid(row=2, column=0, padx=8, pady=4)
        self.old_pw = tk.Entry(master, show="*")
        self.new_pw = tk.Entry(master, show="*")
        self.conf_pw = tk.Entry(master, show="*")
        self.old_pw.grid(row=0, column=1, padx=8, pady=4)
        self.new_pw.grid(row=1, column=1, padx=8, pady=4)
        self.conf_pw.grid(row=2, column=1, padx=8, pady=4)
        return self.old_pw

    def apply(self):
        self.result = (
            self.old_pw.get(),
            self.new_pw.get(),
            self.conf_pw.get()
        )

class ConfigEditor(tk.Toplevel):
    def __init__(self, master, config_file):
        super().__init__(master)
        self.title("Configuration Editor")
        self.geometry("600x500")
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.fields = {}
        self.create_widgets()
        self.load_config()

    def create_widgets(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        self.button_frame = tk.Frame(self)
        self.button_frame.pack(fill="x", padx=10, pady=5)
        tk.Button(self.button_frame, text="Save", command=self.save_config).pack(side="left", padx=5)
        tk.Button(self.button_frame, text="Cancel", command=self.destroy).pack(side="left", padx=5)
        tk.Button(self.button_frame, text="Reload from file", command=self.load_config).pack(side="left", padx=5)
        tk.Button(self.button_frame, text="Change Password", command=self.change_password).pack(side="right", padx=5)

    def load_config(self):
        self.config.read(self.config_file)
        for tab in self.notebook.tabs():
            self.notebook.forget(tab)
        self.fields.clear()
        for section in self.config.sections():
            frame = tk.Frame(self.notebook)
            self.notebook.add(frame, text=section)
            self.fields[section] = {}
            row = 0
            for key, value in self.config[section].items():
                tk.Label(frame, text=key).grid(row=row, column=0, sticky="w", padx=6, pady=4)
                entry = tk.Entry(frame)
                entry.insert(0, value)
                entry.grid(row=row, column=1, sticky="ew", padx=6, pady=4)
                frame.grid_columnconfigure(1, weight=1)
                self.fields[section][key] = entry
                row += 1

    def save_config(self):
        # Validate and update config
        for section, keys in self.fields.items():
            for key, entry in keys.items():
                value = entry.get()
                # Type validation: try to preserve original type
                orig_val = self.config[section][key]
                if orig_val.lower() in ["true", "false"]:
                    if value.lower() not in ["true", "false"]:
                        messagebox.showerror("Validation Error", f"{section}.{key} must be 'true' or 'false'")
                        return
                else:
                    try:
                        if orig_val.isdigit():
                            int(value)
                        else:
                            float(orig_val)
                            float(value)
                    except ValueError:
                        # Allow string if not a number
                        pass
                self.config[section][key] = value
        try:
            backup_file = backup_ini()
            with open(self.config_file, "w") as f:
                self.config.write(f)
            messagebox.showinfo("Success", f"Configuration saved.\nBackup: {backup_file}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save config: {e}")

    def change_password(self):
        dlg = ChangePasswordDialog(self, title="Change Password")
        if dlg.result:
            old_pw, new_pw, conf_pw = dlg.result
            current_pw = get_password_from_ini()
            if old_pw != current_pw:
                messagebox.showerror("Error", "Current password is incorrect.")
                return
            if not new_pw or new_pw != conf_pw:
                messagebox.showerror("Error", "New passwords do not match or are empty.")
                return
            try:
                set_password_in_ini(new_pw)
                messagebox.showinfo("Success", "Password changed successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to change password: {e}")

class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Backgauge Config Test")
        self.geometry("400x300")
        self.create_gear_icon()

    def create_gear_icon(self):
        gear_btn = tk.Button(self, text="⚙️", font=("Arial", 24), command=self.open_password_dialog)
        gear_btn.place(relx=1.0, rely=1.0, anchor="se", x=-10, y=-10)

    def open_password_dialog(self):
        pw = PasswordDialog(self, title="Password Required").result
        if pw is None:
            return
        correct_pw = get_password_from_ini()
        if pw == correct_pw:
            ConfigEditor(self, CONFIG_FILE)
        else:
            messagebox.showerror("Access Denied", "Incorrect password.")

if __name__ == "__main__":
    MainApp().mainloop()