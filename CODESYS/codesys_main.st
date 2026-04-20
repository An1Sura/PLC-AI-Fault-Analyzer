PROGRAM PLC_PRG
VAR
    ScenarioLoader : FB_ScenarioDemoLoader;
END_VAR

ScenarioLoader(
    Execute := GVL_Scenario.LoadScenario,
    ScenarioName := GVL_Scenario.ScenarioName
);

IF ScenarioLoader.Done THEN
    GVL_Scenario.ScenarioLoaded := TRUE;
    GVL_Scenario.LastLoadedScenario := ScenarioLoader.ActiveScenario;
    GVL_Scenario.LoadScenario := FALSE;
END_IF

IF GVL_Diagnostics.Reset_Command THEN
    GVL_Diagnostics.System_Fault_Latch := FALSE;
    GVL_Diagnostics.Sequence_Timeout := FALSE;
    GVL_Diagnostics.HVAC_Fault := FALSE;
    GVL_Diagnostics.Fault_Code := GVL_Constants.FAULT_NONE;
    GVL_Diagnostics.Reset_Command := FALSE;
END_IF

IF (GVL_Diagnostics.Fault_Code <> GVL_Constants.FAULT_NONE) THEN
    GVL_Diagnostics.System_Fault_Latch := TRUE;
END_IF

(* Modbus TCP holding register mapping for portfolio clarity.
   Configure the CODESYS Modbus TCP server so GVL_Diagnostics.HoldingRegs[0..14]
   are exposed as holding registers 0 through 14.

   Register 0  -> Conveyor_Running
   Register 1  -> Sensor_Blocked
   Register 2  -> Motor_Current
   Register 3  -> Safety_OK
   Register 4  -> Start_Command
   Register 5  -> Stop_Command
   Register 6  -> Reset_Command
   Register 7  -> Tank_Level_Low
   Register 8  -> Tank_Level_High
   Register 9  -> Sequence_Timeout
   Register 10 -> System_Fault_Latch
   Register 11 -> Pump_Running
   Register 12 -> HVAC_Fault
   Register 13 -> Mode_Code
   Register 14 -> Fault_Code
*)
GVL_Diagnostics.HoldingRegs[0] := BOOL_TO_UINT(GVL_Diagnostics.Conveyor_Running);
GVL_Diagnostics.HoldingRegs[1] := BOOL_TO_UINT(GVL_Diagnostics.Sensor_Blocked);
GVL_Diagnostics.HoldingRegs[2] := GVL_Diagnostics.Motor_Current;
GVL_Diagnostics.HoldingRegs[3] := BOOL_TO_UINT(GVL_Diagnostics.Safety_OK);
GVL_Diagnostics.HoldingRegs[4] := BOOL_TO_UINT(GVL_Diagnostics.Start_Command);
GVL_Diagnostics.HoldingRegs[5] := BOOL_TO_UINT(GVL_Diagnostics.Stop_Command);
GVL_Diagnostics.HoldingRegs[6] := BOOL_TO_UINT(GVL_Diagnostics.Reset_Command);
GVL_Diagnostics.HoldingRegs[7] := BOOL_TO_UINT(GVL_Diagnostics.Tank_Level_Low);
GVL_Diagnostics.HoldingRegs[8] := BOOL_TO_UINT(GVL_Diagnostics.Tank_Level_High);
GVL_Diagnostics.HoldingRegs[9] := BOOL_TO_UINT(GVL_Diagnostics.Sequence_Timeout);
GVL_Diagnostics.HoldingRegs[10] := BOOL_TO_UINT(GVL_Diagnostics.System_Fault_Latch);
GVL_Diagnostics.HoldingRegs[11] := BOOL_TO_UINT(GVL_Diagnostics.Pump_Running);
GVL_Diagnostics.HoldingRegs[12] := BOOL_TO_UINT(GVL_Diagnostics.HVAC_Fault);
GVL_Diagnostics.HoldingRegs[13] := GVL_Diagnostics.Mode_Code;
GVL_Diagnostics.HoldingRegs[14] := GVL_Diagnostics.Fault_Code;
