FUNCTION_BLOCK FB_ScenarioDemoLoader
VAR_INPUT
    Execute : BOOL;
    ScenarioName : STRING[40];
END_VAR
VAR_OUTPUT
    Done : BOOL;
    ActiveScenario : STRING[40];
END_VAR
VAR
    PreviousExecute : BOOL;
    RisingEdge : BOOL;
END_VAR

RisingEdge := Execute AND NOT PreviousExecute;
PreviousExecute := Execute;

IF RisingEdge THEN
    GVL_Diagnostics.Conveyor_Running := FALSE;
    GVL_Diagnostics.Sensor_Blocked := FALSE;
    GVL_Diagnostics.Motor_Current := 18;
    GVL_Diagnostics.Safety_OK := TRUE;
    GVL_Diagnostics.Start_Command := FALSE;
    GVL_Diagnostics.Stop_Command := FALSE;
    GVL_Diagnostics.Reset_Command := FALSE;
    GVL_Diagnostics.Tank_Level_Low := FALSE;
    GVL_Diagnostics.Tank_Level_High := TRUE;
    GVL_Diagnostics.Sequence_Timeout := FALSE;
    GVL_Diagnostics.System_Fault_Latch := FALSE;
    GVL_Diagnostics.Pump_Running := FALSE;
    GVL_Diagnostics.HVAC_Fault := FALSE;
    GVL_Diagnostics.Mode_Code := GVL_Constants.MODE_IDLE;
    GVL_Diagnostics.Fault_Code := GVL_Constants.FAULT_NONE;

    IF ScenarioName = 'traffic_phase_conflict' THEN
        GVL_Diagnostics.Start_Command := TRUE;
        GVL_Diagnostics.Stop_Command := TRUE;
        GVL_Diagnostics.System_Fault_Latch := TRUE;
        GVL_Diagnostics.Mode_Code := GVL_Constants.MODE_TRAFFIC_CONTROL;
        GVL_Diagnostics.Fault_Code := GVL_Constants.FAULT_TRAFFIC_PHASE_CONFLICT;

    ELSIF ScenarioName = 'pump_station_failure' THEN
        GVL_Diagnostics.Start_Command := TRUE;
        GVL_Diagnostics.Tank_Level_Low := TRUE;
        GVL_Diagnostics.Tank_Level_High := TRUE;
        GVL_Diagnostics.Sequence_Timeout := TRUE;
        GVL_Diagnostics.System_Fault_Latch := TRUE;
        GVL_Diagnostics.Pump_Running := TRUE;
        GVL_Diagnostics.Mode_Code := GVL_Constants.MODE_PUMP_STATION;
        GVL_Diagnostics.Fault_Code := GVL_Constants.FAULT_PUMP_STATION_FAILURE;

    ELSIF ScenarioName = 'elevator_door_fault' THEN
        GVL_Diagnostics.Sensor_Blocked := TRUE;
        GVL_Diagnostics.Safety_OK := FALSE;
        GVL_Diagnostics.Start_Command := TRUE;
        GVL_Diagnostics.Sequence_Timeout := TRUE;
        GVL_Diagnostics.System_Fault_Latch := TRUE;
        GVL_Diagnostics.Mode_Code := GVL_Constants.MODE_ELEVATOR;
        GVL_Diagnostics.Fault_Code := GVL_Constants.FAULT_ELEVATOR_DOOR_TIMEOUT;

    ELSIF ScenarioName = 'tunnel_ventilation_fault' THEN
        GVL_Diagnostics.Start_Command := TRUE;
        GVL_Diagnostics.Sequence_Timeout := TRUE;
        GVL_Diagnostics.System_Fault_Latch := TRUE;
        GVL_Diagnostics.HVAC_Fault := TRUE;
        GVL_Diagnostics.Mode_Code := GVL_Constants.MODE_TUNNEL_VENTILATION;
        GVL_Diagnostics.Fault_Code := GVL_Constants.FAULT_TUNNEL_VENTILATION_FAILURE;

    ELSIF ScenarioName = 'garage_door_fault' THEN
        GVL_Diagnostics.Sensor_Blocked := TRUE;
        GVL_Diagnostics.Safety_OK := FALSE;
        GVL_Diagnostics.Start_Command := TRUE;
        GVL_Diagnostics.Sequence_Timeout := TRUE;
        GVL_Diagnostics.System_Fault_Latch := TRUE;
        GVL_Diagnostics.Mode_Code := GVL_Constants.MODE_GARAGE_DOOR;
        GVL_Diagnostics.Fault_Code := GVL_Constants.FAULT_GARAGE_DOOR_SAFETY_LOCKOUT;

    ELSIF ScenarioName = 'conveyor_jam' THEN
        GVL_Diagnostics.Conveyor_Running := TRUE;
        GVL_Diagnostics.Sensor_Blocked := TRUE;
        GVL_Diagnostics.Motor_Current := 95;
        GVL_Diagnostics.Start_Command := TRUE;
        GVL_Diagnostics.Sequence_Timeout := TRUE;
        GVL_Diagnostics.System_Fault_Latch := TRUE;
        GVL_Diagnostics.Mode_Code := GVL_Constants.MODE_CONVEYOR;
        GVL_Diagnostics.Fault_Code := GVL_Constants.FAULT_CONVEYOR_JAM;

    ELSE
        GVL_Diagnostics.Mode_Code := GVL_Constants.MODE_IDLE;
        GVL_Diagnostics.Fault_Code := GVL_Constants.FAULT_NONE;
    END_IF

    ActiveScenario := ScenarioName;
    Done := TRUE;
ELSE
    Done := FALSE;
END_IF
