# Backgauge Control System

A modular, extensible backgauge control system featuring a Python-based UI and pluggable hardware backends, including both Raspberry Pi GPIO and ESP32-based motion control.

---

## Overview

This project provides a structured control system for a 2-axis backgauge (Depth and Height), with a focus on clean architecture, flexibility, and real-world usability.

The system is designed around a clear separation of responsibilities:

- UI handles user interaction and display
- Controller layer translates intent into motion commands
- Hardware backend executes motion

---

## Key Features

- Dual-axis control (Depth & Height)
- Jogging, presets (Bend 1–4), and homing (in progress)
- Real-time DRO display
- Visual backgauge representation
- Configurable UI via `.ini`
- Multiple hardware backends:
  - Raspberry Pi GPIO (original implementation)
  - ESP32 motion controller over USB serial
- Modular architecture (UI ↔ Controller ↔ Hardware)
- Incremental development approach (safe bring-up on real hardware)

---

## Architecture

UI Layer
  └── backgauge_ui.py

Shared Logic
  └── backgauge_common.py

Controller Layer
  ├── backgauge_controller.py
  └── backgauge_esp32_controller.py

Firmware
  └── esp32/ (PlatformIO project)

---

## Design Philosophy

High-level intent stays on the PC  
Time-critical motion runs on dedicated hardware

---

## Hardware Requirements

### Raspberry Pi Mode

- Raspberry Pi (tested on Pi 3 B+)
- Stepper drivers (tested with DM542T)
- ULN2803 (or similar transistor array)
- Stepper motors
- 5V logic supply
- 24V motor supply
- Common ground

### ESP32 Mode

- ESP32 development board
- Stepper drivers (DM542T or similar)
- Stepper motors
- USB connection to host PC
- Same power considerations as above

---

## ESP32 Firmware

Located in:

esp32/

Built using PlatformIO.

---

## Configuration

Example:

[ui]
mode = esp32
fullscreen = false
update_interval_ms = 100
esp32_port = /dev/ttyUSB0
esp32_baud = 115200

---

## Software Setup

git clone <your-repo-url>
cd backgauge-control

python3 -m venv venv
source venv/bin/activate

pip install customtkinter pyserial

sudo apt install python3-tk

---

## Running

python3 backgauge_ui.py

---

## License

MIT License
