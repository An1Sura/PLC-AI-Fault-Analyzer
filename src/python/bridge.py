from __future__ import annotations

import asyncio
import logging
import os
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import IntEnum
from threading import Lock
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pymodbus.client import ModbusTcpClient

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("plc-fault-analyzer")

REGISTER_COUNT = 15

REGISTER_MAP: dict[int, str] = {
    0: "Conveyor_Running",
    1: "Sensor_Blocked",
    2: "Motor_Current",
    3: "Safety_OK",
    4: "Start_Command",
    5: "Stop_Command",
    6: "Reset_Command",
    7: "Tank_Level_Low",
    8: "Tank_Level_High",
    9: "Sequence_Timeout",
    10: "System_Fault_Latch",
    11: "Pump_Running",
    12: "HVAC_Fault",
    13: "Mode_Code",
    14: "Fault_Code",
}


class ModeCode(IntEnum):
    IDLE = 0
    CONVEYOR = 10
    TRAFFIC_CONTROL = 20
    PUMP_STATION = 30
    ELEVATOR = 40
    TUNNEL_VENTILATION = 50
    GARAGE_DOOR = 60


MODE_NAMES = {
    ModeCode.IDLE: "Idle",
    ModeCode.CONVEYOR: "Conveyor",
    ModeCode.TRAFFIC_CONTROL: "Traffic Control",
    ModeCode.PUMP_STATION: "Pump Station",
    ModeCode.ELEVATOR: "Elevator",
    ModeCode.TUNNEL_VENTILATION: "Tunnel Ventilation",
    ModeCode.GARAGE_DOOR: "Garage Door",
}

FAULT_NAMES = {
    0: "No active fault",
    101: "Traffic phase conflict",
    201: "Pump station level feedback failure",
    301: "Elevator door safety timeout",
    401: "Tunnel ventilation fault",
    501: "Garage door safety lockout",
    601: "Conveyor jam or overload",
}

MOCK_SCENARIOS: dict[str, list[int]] = {
    "idle": [0, 0, 18, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, ModeCode.IDLE, 0],
    "traffic_phase_conflict": [0, 0, 12, 1, 1, 1, 0, 0, 1, 0, 1, 0, 0, ModeCode.TRAFFIC_CONTROL, 101],
    "pump_station_failure": [0, 0, 24, 1, 1, 0, 0, 1, 1, 1, 1, 1, 0, ModeCode.PUMP_STATION, 201],
    "elevator_door_fault": [0, 1, 16, 0, 1, 0, 0, 0, 1, 1, 1, 0, 0, ModeCode.ELEVATOR, 301],
    "tunnel_ventilation_fault": [0, 0, 20, 1, 1, 0, 0, 0, 1, 1, 1, 0, 1, ModeCode.TUNNEL_VENTILATION, 401],
    "garage_door_fault": [0, 1, 15, 0, 1, 0, 0, 0, 1, 1, 1, 0, 0, ModeCode.GARAGE_DOOR, 501],
    "conveyor_jam": [1, 1, 95, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, ModeCode.CONVEYOR, 601],
}


@dataclass(frozen=True)
class BridgeConfig:
    plc_host: str = os.getenv("PLC_HOST", "127.0.0.1")
    plc_port: int = int(os.getenv("PLC_PORT", "502"))
    plc_unit_id: int = int(os.getenv("PLC_UNIT_ID", "1"))
    poll_interval_seconds: float = float(os.getenv("POLL_INTERVAL_SECONDS", "1.0"))
    use_mock_plc: bool = os.getenv("USE_MOCK_PLC", "true").lower() in {"1", "true", "yes", "on"}
    initial_mock_scenario: str = os.getenv("INITIAL_MOCK_SCENARIO", "idle")


class ScenarioRequest(BaseModel):
    scenario: str = Field(..., description="One of the supported demo scenario names.")


class DiagnosticFinding(BaseModel):
    severity: str
    code: int
    title: str
    evidence: list[str]
    recommendation: str


class DiagnosticsResponse(BaseModel):
    timestamp: str
    healthy: bool
    machine_state: str
    active_fault_code: int
    findings: list[DiagnosticFinding]


class PLCState(BaseModel):
    timestamp: str
    connected: bool
    source: str
    registers: dict[str, int]
    raw_registers: list[int]
    machine_state: str
    active_fault_code: int
    active_fault_name: str


class PLCBridge:
    def __init__(self, config: BridgeConfig) -> None:
        self.config = config
        self._client = ModbusTcpClient(host=config.plc_host, port=config.plc_port, timeout=2.0)
        self._lock = Lock()
        initial = MOCK_SCENARIOS.get(config.initial_mock_scenario, MOCK_SCENARIOS["idle"])
        self._registers = [int(value) for value in initial]
        self._connected = config.use_mock_plc
        self._source = "mock" if config.use_mock_plc else "modbus"
        self._last_fault_code = self._registers[14]
        self._events: deque[dict[str, Any]] = deque(maxlen=200)
        self._record_event("bridge_started", f"Diagnostics bridge started using {self._source} source.")

    def state(self) -> PLCState:
        with self._lock:
            registers = list(self._registers)
            connected = self._connected
            source = self._source

        fault_code = registers[14]
        return PLCState(
            timestamp=utc_now(),
            connected=connected,
            source=source,
            registers={REGISTER_MAP[index]: registers[index] for index in range(REGISTER_COUNT)},
            raw_registers=registers,
            machine_state=detect_machine_state(registers),
            active_fault_code=fault_code,
            active_fault_name=FAULT_NAMES.get(fault_code, "Unknown fault"),
        )

    def events(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._events)

    def set_mock_scenario(self, scenario: str) -> PLCState:
        if scenario not in MOCK_SCENARIOS:
            raise ValueError(f"Unsupported scenario '{scenario}'.")

        with self._lock:
            self._registers = [int(value) for value in MOCK_SCENARIOS[scenario]]
            self._connected = True
            self._source = "mock"
            self._last_fault_code = self._registers[14]
            self._record_event("mock_scenario_loaded", f"Loaded mock scenario '{scenario}'.")

        return self.state()

    async def poll_forever(self) -> None:
        while True:
            try:
                if self._source == "mock" or self.config.use_mock_plc:
                    self._evaluate_fault_transition()
                else:
                    self.poll_modbus_once()
            except Exception:
                logger.exception("PLC polling cycle failed")
            await asyncio.sleep(self.config.poll_interval_seconds)

    def poll_modbus_once(self) -> None:
        if not self._client.connected and not self._client.connect():
            self._set_connection_state(False)
            return

        try:
            response = self._client.read_holding_registers(
                address=0,
                count=REGISTER_COUNT,
                slave=self.config.plc_unit_id,
            )
        except TypeError:
            response = self._client.read_holding_registers(
                address=0,
                count=REGISTER_COUNT,
                unit=self.config.plc_unit_id,
            )

        if response.isError():
            self._set_connection_state(False)
            self._record_event("modbus_error", str(response))
            return

        values = [int(value) for value in response.registers[:REGISTER_COUNT]]
        if len(values) != REGISTER_COUNT:
            self._set_connection_state(False)
            self._record_event("modbus_error", f"Expected 15 registers but received {len(values)}.")
            return

        with self._lock:
            self._registers = values
            self._connected = True
            self._source = "modbus"

        self._evaluate_fault_transition()

    def _set_connection_state(self, connected: bool) -> None:
        with self._lock:
            if self._connected != connected:
                state = "connected" if connected else "disconnected"
                self._record_event("connection_state_changed", f"PLC Modbus client {state}.")
            self._connected = connected

    def _evaluate_fault_transition(self) -> None:
        with self._lock:
            fault_code = self._registers[14]
            if fault_code != self._last_fault_code:
                fault_name = FAULT_NAMES.get(fault_code, "Unknown fault")
                self._record_event("fault_code_changed", f"Fault changed to {fault_code}: {fault_name}.")
                self._last_fault_code = fault_code

    def _record_event(self, event_type: str, message: str) -> None:
        self._events.appendleft(
            {
                "timestamp": utc_now(),
                "type": event_type,
                "message": message,
            }
        )


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def bool_reg(registers: list[int], index: int) -> bool:
    return registers[index] != 0


def detect_machine_state(registers: list[int]) -> str:
    mode_value = registers[13]
    mode_name = MODE_NAMES.get(ModeCode(mode_value), "Unknown") if mode_value in ModeCode._value2member_map_ else "Unknown"

    if bool_reg(registers, 10):
        return f"{mode_name} - Faulted"
    if bool_reg(registers, 4) and not bool_reg(registers, 5):
        return f"{mode_name} - Running"
    if bool_reg(registers, 5):
        return f"{mode_name} - Stopping"
    return f"{mode_name} - Ready"


def run_diagnostics(state: PLCState) -> DiagnosticsResponse:
    r = state.raw_registers
    findings: list[DiagnosticFinding] = []
    fault_code = state.active_fault_code

    if not state.connected:
        findings.append(
            DiagnosticFinding(
                severity="critical",
                code=-1,
                title="PLC communication unavailable",
                evidence=[f"Source '{state.source}' is not connected."],
                recommendation="Verify PLC power, IP address, Modbus TCP server configuration, firewall rules, and network cabling.",
            )
        )

    if bool_reg(r, 10):
        findings.append(
            DiagnosticFinding(
                severity="high",
                code=fault_code,
                title=FAULT_NAMES.get(fault_code, "Latched system fault"),
                evidence=["System_Fault_Latch is active.", f"Fault_Code is {fault_code}."],
                recommendation="Review the active fault, correct the field condition, then issue Reset_Command after the process is safe.",
            )
        )

    if bool_reg(r, 0) and bool_reg(r, 1) and r[2] >= 80:
        findings.append(
            DiagnosticFinding(
                severity="critical",
                code=601,
                title="Conveyor jam or overload",
                evidence=[
                    "Conveyor_Running is true.",
                    "Sensor_Blocked is true.",
                    f"Motor_Current is {r[2] / 10:.1f} A.",
                ],
                recommendation="Stop the conveyor, clear the obstruction, inspect the motor load path, and verify the photoeye before restart.",
            )
        )

    if bool_reg(r, 11) and bool_reg(r, 7) and bool_reg(r, 8):
        findings.append(
            DiagnosticFinding(
                severity="high",
                code=201,
                title="Pump station level feedback conflict",
                evidence=["Pump_Running is true.", "Tank_Level_Low and Tank_Level_High are both true."],
                recommendation="Inspect level switches, wet well wiring, and input scaling. Do not run the pump automatically until feedback is credible.",
            )
        )

    if bool_reg(r, 12):
        findings.append(
            DiagnosticFinding(
                severity="high",
                code=401,
                title="Ventilation fault active",
                evidence=["HVAC_Fault is true."],
                recommendation="Check fan starter feedback, VFD fault status, airflow proving switch, and emergency ventilation permissives.",
            )
        )

    if not bool_reg(r, 3):
        findings.append(
            DiagnosticFinding(
                severity="critical",
                code=501 if fault_code == 501 else fault_code,
                title="Safety chain is not healthy",
                evidence=["Safety_OK is false."],
                recommendation="Validate E-stop, guard door, light curtain, safety relay, and reset circuit before enabling motion.",
            )
        )

    if bool_reg(r, 9):
        findings.append(
            DiagnosticFinding(
                severity="medium",
                code=301 if fault_code == 301 else fault_code,
                title="Sequence timeout",
                evidence=["Sequence_Timeout is true."],
                recommendation="Check actuator travel, permissive inputs, sensor timing, and step transition logic for the active mode.",
            )
        )

    if bool_reg(r, 4) and bool_reg(r, 5):
        findings.append(
            DiagnosticFinding(
                severity="medium",
                code=101,
                title="Conflicting operator commands",
                evidence=["Start_Command and Stop_Command are both true."],
                recommendation="Check HMI command latching, momentary pushbutton wiring, and command arbitration logic.",
            )
        )

    if not findings:
        findings.append(
            DiagnosticFinding(
                severity="info",
                code=0,
                title="No active diagnostic findings",
                evidence=["No fault latch or abnormal register combinations are active."],
                recommendation="Continue monitoring. Confirm field devices during scheduled maintenance.",
            )
        )

    return DiagnosticsResponse(
        timestamp=utc_now(),
        healthy=all(item.severity == "info" for item in findings),
        machine_state=state.machine_state,
        active_fault_code=fault_code,
        findings=findings,
    )


config = BridgeConfig()
bridge = PLCBridge(config)
app = FastAPI(
    title="PLC Fault Analyzer",
    description="Industrial diagnostics bridge for CODESYS, Modbus TCP, FastAPI, and ESP32 demos.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    asyncio.create_task(bridge.poll_forever())


@app.get("/health")
async def health() -> dict[str, Any]:
    state = bridge.state()
    return {
        "status": "ok" if state.connected else "degraded",
        "timestamp": utc_now(),
        "plc_connected": state.connected,
        "source": state.source,
    }


@app.get("/api/state", response_model=PLCState)
async def api_state() -> PLCState:
    return bridge.state()


@app.get("/api/events")
async def api_events() -> dict[str, Any]:
    return {"events": bridge.events()}


@app.get("/api/diagnostics", response_model=DiagnosticsResponse)
async def api_diagnostics() -> DiagnosticsResponse:
    return run_diagnostics(bridge.state())


@app.post("/api/mock/scenario", response_model=PLCState)
async def api_mock_scenario(request: ScenarioRequest) -> PLCState:
    try:
        return bridge.set_mock_scenario(request.scenario)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"message": str(exc), "supported_scenarios": sorted(MOCK_SCENARIOS)},
        ) from exc


@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            state = bridge.state()
            diagnostics = run_diagnostics(state)
            await websocket.send_json(
                {
                    "state": state.model_dump(),
                    "diagnostics": diagnostics.model_dump(),
                }
            )
            await asyncio.sleep(config.poll_interval_seconds)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "bridge:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=False,
    )
