# PLC Fault Analyzer

## Project Overview

PLC Fault Analyzer is an industrial diagnostics bridge that connects PLC logic, Modbus TCP data, a Python API layer, and an embedded ESP32 client into one coherent troubleshooting system. It is built to demonstrate how real automation faults can be surfaced, classified, and explained across controls and software boundaries.

The project models a small industrial cell where CODESYS publishes machine status through holding registers, FastAPI converts raw register values into useful diagnostics, and an ESP32 client independently polls the same PLC data for embedded field visibility.

## Architecture

```text
CODESYS PLC Structured Text
    Holding registers 0-14
            |
            | Modbus TCP
            v
Python FastAPI Bridge
    Polling, state detection, event history, diagnostics API, WebSocket stream
            |
            | HTTP / WebSocket
            v
Operator tools, dashboards, test clients

ESP32 Embedded Client
    WiFi + Modbus TCP polling of the same PLC register map
```

## Features

- CODESYS Structured Text logic for machine state, fault latches, and scenario loading.
- Fixed Modbus TCP holding register map from address `0` through `14`.
- Python FastAPI bridge with live polling, diagnostics, event history, mock scenarios, and WebSocket streaming.
- Rule-based diagnostics engine for common industrial fault modes.
- ESP32 WiFi client that polls PLC holding registers and prints decoded values to Serial.
- CAD enclosure assets for a small ESP32 diagnostics module.
- Repository layout suitable for an engineering portfolio or practical controls/software integration demo.

## Register Map

| Register | Tag | Description |
| --- | --- | --- |
| 0 | `Conveyor_Running` | Conveyor motor command/status |
| 1 | `Sensor_Blocked` | Product/photoeye blockage |
| 2 | `Motor_Current` | Motor current in tenths of amps |
| 3 | `Safety_OK` | Safety chain healthy |
| 4 | `Start_Command` | Start request |
| 5 | `Stop_Command` | Stop request |
| 6 | `Reset_Command` | Fault reset request |
| 7 | `Tank_Level_Low` | Low level switch |
| 8 | `Tank_Level_High` | High level switch |
| 9 | `Sequence_Timeout` | Sequence watchdog timeout |
| 10 | `System_Fault_Latch` | Latched system fault |
| 11 | `Pump_Running` | Pump status |
| 12 | `HVAC_Fault` | Ventilation/HVAC fault |
| 13 | `Mode_Code` | Active machine mode |
| 14 | `Fault_Code` | Active fault code |

## Demo Scenarios

- `idle`: healthy system with no active fault.
- `traffic_phase_conflict`: simultaneous command conflict represented by fault `101`.
- `pump_station_failure`: pump is running with invalid tank level feedback, fault `201`.
- `elevator_door_fault`: sequence timeout and safety fault, fault `301`.
- `tunnel_ventilation_fault`: HVAC fault in tunnel ventilation mode, fault `401`.
- `garage_door_fault`: safety chain open with a blocked sensor, fault `501`.
- `conveyor_jam`: conveyor running with blocked sensor and high current, fault `601`.

## Setup Instructions

### Python Bridge

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python src/python/bridge.py
```

Default API URL:

```text
http://127.0.0.1:8000
```

Useful endpoints:

- `GET /health`
- `GET /api/state`
- `GET /api/events`
- `GET /api/diagnostics`
- `POST /api/mock/scenario`
- `WS /ws/live`

Example mock scenario request:

```bash
curl -X POST http://127.0.0.1:8000/api/mock/scenario \
  -H "Content-Type: application/json" \
  -d '{"scenario":"conveyor_jam"}'
```

### CODESYS Setup

1. Create a CODESYS project using a runtime that supports Modbus TCP server operation.
2. Add the Structured Text files from `CODESYS/` as global variable lists, a function block, and the main PLC program.
3. Enable a Modbus TCP server/slave device.
4. Map the exported holding register array `GVL_Diagnostics.HoldingRegs[0..14]` to Modbus holding registers `0..14`.
5. Run the PLC project and set `GVL_Scenario.ScenarioName` plus `GVL_Scenario.LoadScenario` to load demo conditions.

### ESP32 Setup

1. Install the ESP32 board package in the Arduino IDE.
2. Install the `ArduinoModbus` library.
3. Open `firmware/esp32/esp32_diagnostics.ino`.
4. Set `WIFI_SSID`, `WIFI_PASSWORD`, and `PLC_HOST`.
5. Upload to the ESP32.
6. Open Serial Monitor at `115200` baud.

## Folder Structure

```text
plc-fault-analyzer/
├── README.md
├── requirements.txt
├── .env.example
├── src/python/bridge.py
├── firmware/esp32/esp32_diagnostics.ino
├── CODESYS/
│   ├── codesys_globals.st
│   ├── codesys_constants.st
│   ├── codesys_scenario_globals.st
│   ├── codesys_fb_scenario_demo_loader.st
│   └── codesys_main.st
└── CAD/
    ├── ESP32ModuleBase.stl
    └── ESP32ModuleTop.stl
```

## CAD Section

The `CAD/` directory contains STL enclosure components for an ESP32 diagnostics module:

- `ESP32ModuleBase.stl`: lower tray for the embedded diagnostics module.
- `ESP32ModuleTop.stl`: matching cover plate.

The CAD assets are included so the project can be presented as a complete hardware/software diagnostic bridge rather than only an API demo.

## Project Goal

Modern plants rarely fail inside one clean boundary. A troubleshooting workflow often crosses PLC logic, fieldbus/register data, backend services, embedded devices, and physical hardware. This project demonstrates that bridge: raw PLC signals are converted into readable system state, fault events, and actionable diagnostics while preserving the register-level truth that controls engineers need.

## Summary

Designed and implemented an industrial PLC diagnostics bridge integrating CODESYS Structured Text, Modbus TCP, Python FastAPI, WebSocket telemetry, ESP32 embedded polling, and CAD enclosure assets. Built a fixed register interface, fault simulation scenarios, and a rule-based diagnostics engine for realistic automation troubleshooting workflows.
