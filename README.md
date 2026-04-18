# Backgauge Control System

A Python-based backgauge control system designed for a Raspberry Pi, featuring a modern touchscreen UI, and hardware control using stepper drivers.

---

## Overview

This project provides a structured and extensible control system for a 2-axis backgauge (Depth and Height), with:

- Clean UI (CustomTkinter)
- Hardware mode for real stepper control
- Modular architecture (UI ↔ Controller ↔ Hardware)

Originally developed as a prototype, now evolved into a working motion control foundation.

---

## Features

- Dual-axis control (Depth & Height)
- Jogging, presets (Bend 1–4), and homing
- Real-time DRO updates
- Visual backgauge representation
- Hardware backend (Raspberry Pi + stepper drivers)
- Threaded motion control (non-blocking UI)

---

## Architecture

UI Layer
  └── backgauge_ui.py

Shared Logic
  └── backgauge_common.py

Controllers
  └── backgauge_controller.py

### Key Design Principle

Motion control is isolated from UI updates to maintain smooth stepper operation.

---

## Hardware Requirements

- Raspberry Pi (tested on Pi 3 B+)
- Stepper drivers (tested with DM542T)
- Stepper motors
- ULN2803 (or similar transistor array) for signal interfacing
- 5V power supply (logic)
- 24V power supply (motor)
- Shared ground between all systems

---

## Wiring (Typical Setup)

Using ULN2803 (recommended)

Example (Depth axis)

Signal | Pi Pin | ULN2803 | Driver
------ | ------ | ------- | ------
STEP   | 11     | IN1 → OUT18 | PUL-
DIR    | 29     | IN2 → OUT17 | DIR-
+5V    | —      | —           | PUL+, DIR+

- ULN2803 pin 9 → GND
- All grounds shared

---

## Software Setup

### 1. Clone repository

git clone <your-repo-url>
cd backgauge-control

### 2. Create virtual environment

python3 -m venv venv
source venv/bin/activate

### 3. Install dependencies

pip install customtkinter
pip install RPi.GPIO

On Raspberry Pi, you may also use:
sudo apt install python3-rpi.gpio

---

## Running the Application

python backgauge_ui.py

---


## Motion Behavior

- Step pulses generated in a dedicated worker thread
- UI updates are decoupled from motion loop
- Incremental position tracking during movement
- Adjustable update rate for performance tuning

---

## Known Limitations

- Step timing uses Python time.sleep() (non-real-time)
- No acceleration/deceleration yet
- Limit switches wired but basic handling only

---

## Future Improvements

- Proper step timing calculation (RPM-based)
- Acceleration / deceleration (ramping)
- Full homing routine using limit switches
- Improved UI performance (optional reduced redraw during motion)
- Optional migration to hardware-timed pulses (e.g., pigpio)

---

## Development Notes

- Built incrementally from a UI prototype
- Designed for clarity and maintainability
- Emphasis on separating:
  - UI logic
  - motion logic
  - hardware interface

---

## License

MIT License
