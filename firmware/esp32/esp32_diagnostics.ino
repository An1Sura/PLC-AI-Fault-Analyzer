#include <ArduinoModbus.h>
#include <WiFi.h>

const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* PLC_HOST = "192.168.1.50";
const uint16_t PLC_PORT = 502;
const uint8_t PLC_UNIT_ID = 1;

const uint16_t REGISTER_START = 0;
const uint16_t REGISTER_COUNT = 15;
const unsigned long POLL_INTERVAL_MS = 1000;
const unsigned long WIFI_RETRY_MS = 5000;

WiFiClient wifiClient;
ModbusTCPClient modbusClient(wifiClient);

unsigned long lastPollMs = 0;
unsigned long lastWifiAttemptMs = 0;

const char* registerNames[REGISTER_COUNT] = {
  "Conveyor_Running",
  "Sensor_Blocked",
  "Motor_Current",
  "Safety_OK",
  "Start_Command",
  "Stop_Command",
  "Reset_Command",
  "Tank_Level_Low",
  "Tank_Level_High",
  "Sequence_Timeout",
  "System_Fault_Latch",
  "Pump_Running",
  "HVAC_Fault",
  "Mode_Code",
  "Fault_Code"
};

void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  unsigned long now = millis();
  if (now - lastWifiAttemptMs < WIFI_RETRY_MS) {
    return;
  }

  lastWifiAttemptMs = now;
  Serial.print("Connecting to WiFi SSID ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

bool ensureModbusConnection() {
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }

  if (modbusClient.connected()) {
    return true;
  }

  Serial.print("Connecting to Modbus TCP server ");
  Serial.print(PLC_HOST);
  Serial.print(":");
  Serial.println(PLC_PORT);

  if (!modbusClient.begin(PLC_HOST, PLC_PORT)) {
    Serial.print("Modbus connection failed: ");
    Serial.println(modbusClient.lastError());
    return false;
  }

  modbusClient.setTimeout(2000);
  Serial.println("Modbus TCP connected");
  return true;
}

void printWiFiStatus() {
  static wl_status_t previousStatus = WL_IDLE_STATUS;
  wl_status_t currentStatus = WiFi.status();

  if (currentStatus == previousStatus) {
    return;
  }

  previousStatus = currentStatus;

  if (currentStatus == WL_CONNECTED) {
    Serial.print("WiFi connected, IP=");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("WiFi disconnected");
    modbusClient.stop();
  }
}

void pollHoldingRegisters() {
  if (!ensureModbusConnection()) {
    return;
  }

  int received = modbusClient.requestFrom(PLC_UNIT_ID, HOLDING_REGISTERS, REGISTER_START, REGISTER_COUNT);
  if (received != REGISTER_COUNT) {
    Serial.print("Register poll failed: ");
    Serial.println(modbusClient.lastError());
    modbusClient.stop();
    return;
  }

  Serial.println("---- PLC Holding Registers 0-14 ----");
  for (uint16_t index = 0; index < REGISTER_COUNT; index++) {
    int value = modbusClient.read();
    Serial.print(index);
    Serial.print(" ");
    Serial.print(registerNames[index]);
    Serial.print(" = ");
    Serial.println(value);
  }
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("LogicLatch ESP32 Diagnostics Client");
  connectWiFi();
}

void loop() {
  connectWiFi();
  printWiFiStatus();

  unsigned long now = millis();
  if (now - lastPollMs >= POLL_INTERVAL_MS) {
    lastPollMs = now;
    pollHoldingRegisters();
  }
}
