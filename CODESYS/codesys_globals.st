{attribute 'qualified_only'}
VAR_GLOBAL
    Conveyor_Running : BOOL := FALSE;
    Sensor_Blocked : BOOL := FALSE;
    Motor_Current : UINT := 18;
    Safety_OK : BOOL := TRUE;
    Start_Command : BOOL := FALSE;
    Stop_Command : BOOL := FALSE;
    Reset_Command : BOOL := FALSE;
    Tank_Level_Low : BOOL := FALSE;
    Tank_Level_High : BOOL := TRUE;
    Sequence_Timeout : BOOL := FALSE;
    System_Fault_Latch : BOOL := FALSE;
    Pump_Running : BOOL := FALSE;
    HVAC_Fault : BOOL := FALSE;
    Mode_Code : UINT := GVL_Constants.MODE_IDLE;
    Fault_Code : UINT := GVL_Constants.FAULT_NONE;

    HoldingRegs : ARRAY[0..14] OF UINT;
END_VAR
