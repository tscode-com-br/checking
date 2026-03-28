#include <WiFi.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <MFRC522.h>

#if defined(__INTELLISENSE__)
// IntelliSense shim: runtime build still uses the real ESP32 WiFi definitions.
typedef enum {
  WL_IDLE_STATUS = 0,
  WL_NO_SSID_AVAIL = 1,
  WL_SCAN_COMPLETED = 2,
  WL_CONNECTED = 3,
  WL_CONNECT_FAILED = 4,
  WL_CONNECTION_LOST = 5,
  WL_DISCONNECTED = 6
} wl_status_t;

class WiFiIntellisenseShim {
public:
  wl_status_t status() { return WL_DISCONNECTED; }
  void disconnect(bool wifioff = false, bool eraseap = false) {
    (void)wifioff;
    (void)eraseap;
  }
  void mode(int m) { (void)m; }
  void setSleep(bool enabled) { (void)enabled; }
  void begin(const char* ssid, const char* passphrase) {
    (void)ssid;
    (void)passphrase;
  }
  const char* localIP() { return "0.0.0.0"; }
};

extern WiFiIntellisenseShim WiFi;

#ifndef WIFI_STA
#define WIFI_STA 1
#endif
#endif

const char* WIFI_SSID = "TS 14 PRO";
const char* WIFI_PASSWORD = "00000000";
const char* API_HOST = "157.230.35.21";
const char* DEVICE_ID = "ESP32-S3-01";
const char* SHARED_KEY = "gyb2YCkwhDFkhhYQQC6W80BafOf9YsTr";
const char* DEVICE_LOCATION = "main";

const int API_PORTS[] = {8000, 8001};
const int API_PORTS_COUNT = 2;

const int RFID_SCK_PIN = 12;
const int RFID_MISO_PIN = 13;
const int RFID_MOSI_PIN = 11;
const int RFID_RST_PIN = 9;
const int RFID_SENSOR_1_SS_PIN = 10;
const int RFID_SENSOR_2_SS_PIN = 14;

struct ReaderSlot {
  MFRC522 reader;
  const char* sensorName;
  const char* actionName;
  byte ssPin;
  bool ready;
  unsigned long lastScanAt;

  ReaderSlot(byte ssPinValue, byte rstPinValue, const char* sensorNameValue, const char* actionNameValue)
      : reader(ssPinValue, rstPinValue), sensorName(sensorNameValue), actionName(actionNameValue), ssPin(ssPinValue), ready(false), lastScanAt(0) {}
};

ReaderSlot readers[] = {
  ReaderSlot(RFID_SENSOR_1_SS_PIN, RFID_RST_PIN, "sensor-1", "checkin"),
  ReaderSlot(RFID_SENSOR_2_SS_PIN, RFID_RST_PIN, "sensor-2", "checkout")
};

const int READER_COUNT = sizeof(readers) / sizeof(readers[0]);

unsigned long lastHeartbeat = 0;
unsigned long lastReaderRetry = 0;
unsigned long nextCloudAttemptAt = 0;
unsigned long offlineSince = 0;

const unsigned long HEARTBEAT_MS = 180000;
const unsigned long SCAN_COOLDOWN_MS = 1200;
const unsigned long CLOUD_RETRY_MS = 30000;
const unsigned long OFFLINE_RESTART_MS = 30000;
const unsigned long READER_RETRY_MS = 5000;

int activeApiPort = 0;

unsigned long lastDiagPrint = 0;
const unsigned long DIAG_PRINT_MS = 10000;

enum CloudStatus {
  CLOUD_CONNECTING,
  CLOUD_ONLINE,
  CLOUD_OFFLINE
};

CloudStatus cloudStatus = CLOUD_CONNECTING;

unsigned long lastStatusBlinkAt = 0;
unsigned long statusLedOnUntil = 0;
bool statusLedPulseActive = false;
const unsigned long STATUS_BLINK_INTERVAL_MS = 1000;
const unsigned long STATUS_BLINK_ON_MS = 100;

void setInternalLedOff() {
#ifdef RGB_BUILTIN
  neopixelWrite(RGB_BUILTIN, 0, 0, 0);
#endif
}

void setInternalLedWhite() {
#ifdef RGB_BUILTIN
  neopixelWrite(RGB_BUILTIN, 255, 255, 255);
#endif
}

void setInternalLedYellow() {
#ifdef RGB_BUILTIN
  neopixelWrite(RGB_BUILTIN, 255, 255, 0);
#endif
}

void setInternalLedOrange() {
#ifdef RGB_BUILTIN
  neopixelWrite(RGB_BUILTIN, 255, 80, 0);
#endif
}

void setInternalLedGreen() {
#ifdef RGB_BUILTIN
  neopixelWrite(RGB_BUILTIN, 0, 255, 0);
#endif
}

void setInternalLedRed() {
#ifdef RGB_BUILTIN
  neopixelWrite(RGB_BUILTIN, 255, 0, 0);
#endif
}

void resetStatusBlink() {
  lastStatusBlinkAt = 0;
  statusLedOnUntil = 0;
  statusLedPulseActive = false;
}

bool anyReaderNotReady() {
  for (int i = 0; i < READER_COUNT; i++) {
    if (!readers[i].ready) {
      return true;
    }
  }
  return false;
}

void applyCloudLedBaseline() {
  if (cloudStatus == CLOUD_CONNECTING) {
    resetStatusBlink();
    setInternalLedYellow();
    return;
  }

  if (cloudStatus == CLOUD_OFFLINE) {
    resetStatusBlink();
    setInternalLedRed();
    return;
  }

  setInternalLedOff();
}

void pulseGreenSuccess() {
  setInternalLedGreen();
  delay(2000);
  applyCloudLedBaseline();
}

void holdOrangePending() {
  setInternalLedOrange();
  delay(4000);
  applyCloudLedBaseline();
}

void startupLedTest() {
  setInternalLedYellow();
}

void setCloudConnecting() {
  cloudStatus = CLOUD_CONNECTING;
  applyCloudLedBaseline();
}

void setCloudOnline() {
  cloudStatus = CLOUD_ONLINE;
  offlineSince = 0;
  resetStatusBlink();
  setInternalLedOff();
}

void setCloudOffline() {
  cloudStatus = CLOUD_OFFLINE;
  if (offlineSince == 0) {
    offlineSince = millis();
  }
  applyCloudLedBaseline();
}

bool canProcessCardReads() {
  return cloudStatus == CLOUD_ONLINE;
}

void restartIfOfflineTooLong() {
  if (cloudStatus != CLOUD_OFFLINE || offlineSince == 0) {
    return;
  }

  if (millis() - offlineSince < OFFLINE_RESTART_MS) {
    return;
  }

  Serial.println("[NET] Offline for 30s. Restarting ESP32 to retry Wi-Fi and cloud connection.");
  delay(100);
  ESP.restart();
}

void updateStatusLed() {
  unsigned long now = millis();

  if (cloudStatus == CLOUD_CONNECTING || cloudStatus == CLOUD_OFFLINE) {
    applyCloudLedBaseline();
    return;
  }

  if (statusLedPulseActive && (long)(now - statusLedOnUntil) >= 0) {
    setInternalLedOff();
    statusLedPulseActive = false;
  }

  if (!statusLedPulseActive && (lastStatusBlinkAt == 0 || now - lastStatusBlinkAt >= STATUS_BLINK_INTERVAL_MS)) {
    lastStatusBlinkAt = now;
    statusLedOnUntil = now + STATUS_BLINK_ON_MS;
    setInternalLedWhite();
    statusLedPulseActive = true;
  }
}

String uidToString(uint8_t* uid, uint8_t uidLength) {
  String out = "";
  for (uint8_t i = 0; i < uidLength; i++) {
    if (uid[i] < 0x10) {
      out += "0";
    }
    out += String(uid[i], HEX);
  }
  out.toUpperCase();
  return out;
}

byte readReaderVersion(ReaderSlot& slot) {
  return slot.reader.PCD_ReadRegister(MFRC522::VersionReg);
}

String buildApiUrl(const char* path, int port) {
  return String("http://") + String(API_HOST) + ":" + String(port) + String(path);
}

int detectApiPort() {
  if (WiFi.status() != WL_CONNECTED) {
    return 0;
  }

  for (int i = 0; i < API_PORTS_COUNT; i++) {
    int candidate = API_PORTS[i];
    HTTPClient http;
    String url = buildApiUrl("/api/health", candidate);
    if (!http.begin(url)) {
      continue;
    }
    int code = http.GET();
    String body = http.getString();
    http.end();

    if (code >= 200 && code < 300 && body.indexOf("\"status\":\"ok\"") >= 0) {
      return candidate;
    }
  }
  return 0;
}

bool sendHeartbeat() {
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }

  if (activeApiPort == 0) {
    activeApiPort = detectApiPort();
    if (activeApiPort == 0) {
      Serial.println("[NET] API not reachable on 8000/8001");
      return false;
    }
    Serial.print("[NET] API port detected: ");
    Serial.println(activeApiPort);
  }

  HTTPClient http;
  String url = buildApiUrl("/api/device/heartbeat", activeApiPort);
  if (!http.begin(url)) {
    return false;
  }

  http.addHeader("Content-Type", "application/json");
  String body = "{\"device_id\":\"" + String(DEVICE_ID) + "\",\"shared_key\":\"" + String(SHARED_KEY) + "\"}";
  int code = http.POST(body);
  String response = http.getString();
  http.end();

  bool httpOk = code >= 200 && code < 300;
  bool appOk = response.indexOf("\"ok\":true") >= 0 || response.indexOf("\"ok\": true") >= 0;
  bool appExplicitFail = response.indexOf("\"ok\":false") >= 0 || response.indexOf("\"ok\": false") >= 0;
  bool ok = httpOk && (appOk || !appExplicitFail);
  if (!ok) {
    Serial.print("[NET] Heartbeat failed. HTTP=");
    Serial.println(code);
    Serial.print("[NET] Heartbeat body=");
    Serial.println(response);
    if (code <= 0) {
      activeApiPort = 0;
    }
  }
  return ok;
}

bool ensureWifiConnected() {
  if (WiFi.status() == WL_CONNECTED) {
    return true;
  }

  Serial.print("[NET] Connecting Wi-Fi SSID=");
  Serial.println(WIFI_SSID);

  WiFi.disconnect(true, true);
  delay(150);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 20000) {
    delay(300);
  }

  wl_status_t status = WiFi.status();
  if (status != WL_CONNECTED) {
    Serial.print("[NET] Wi-Fi connect failed. status=");
    Serial.println((int)status);
    activeApiPort = 0;
    return false;
  }

  Serial.print("[NET] Wi-Fi connected. IP: ");
  Serial.println(WiFi.localIP());
  return true;
}

bool attemptCloudHandshake() {
  setCloudConnecting();

  if (!ensureWifiConnected()) {
    setCloudOffline();
    nextCloudAttemptAt = millis() + CLOUD_RETRY_MS;
    return false;
  }

  if (sendHeartbeat()) {
    Serial.println("[NET] Cloud heartbeat acknowledged.");
    lastHeartbeat = millis();
    nextCloudAttemptAt = 0;
    setCloudOnline();
    return true;
  }

  Serial.println("[NET] Cloud heartbeat failed.");
  setCloudOffline();
  nextCloudAttemptAt = millis() + CLOUD_RETRY_MS;
  return false;
}

String sendScan(const String& uid, const char* action, const char* sensorName) {
  if (WiFi.status() != WL_CONNECTED) {
    return "network_error";
  }

  if (activeApiPort == 0) {
    activeApiPort = detectApiPort();
    if (activeApiPort == 0) {
      return "api_unreachable";
    }
  }

  HTTPClient http;
  String url = buildApiUrl("/api/scan", activeApiPort);
  if (!http.begin(url)) {
    return "http_init_error";
  }

  String requestId = String(DEVICE_ID) + "-" + String(sensorName) + "-" + String(millis()) + "-" + uid;

  String body = "{";
  body += "\"rfid\":\"" + uid + "\",";
  body += "\"local\":\"" + String(DEVICE_LOCATION) + "\",";
  body += "\"action\":\"" + String(action) + "\",";
  body += "\"device_id\":\"" + String(DEVICE_ID) + "\",";
  body += "\"request_id\":\"" + requestId + "\",";
  body += "\"shared_key\":\"" + String(SHARED_KEY) + "\"";
  body += "}";

  http.addHeader("Content-Type", "application/json");
  int code = http.POST(body);
  String response = http.getString();
  http.end();

  if (code < 200 || code >= 300) {
    if (code <= 0) {
      activeApiPort = 0;
    }
    return "http_error";
  }

  return response;
}

bool initReader(ReaderSlot& slot) {
  digitalWrite(slot.ssPin, HIGH);
  slot.reader.PCD_Init();
  delay(50);

  byte version = readReaderVersion(slot);
  if (version == 0x00 || version == 0xFF) {
    Serial.print("[RC522] ");
    Serial.print(slot.sensorName);
    Serial.println(" sem resposta no barramento SPI");
    slot.ready = false;
    return false;
  }

  slot.reader.PCD_AntennaOn();
  slot.ready = true;
  Serial.print("[RC522] ");
  Serial.print(slot.sensorName);
  Serial.print(" version=0x");
  Serial.print(version, HEX);
  Serial.print(" action=");
  Serial.println(slot.actionName);
  return true;
}

void initReaderIfNeeded() {
  bool allReady = true;

  for (int i = 0; i < READER_COUNT; i++) {
    if (!readers[i].ready) {
      if (!initReader(readers[i])) {
        allReady = false;
      }
    }
  }

  Serial.print("[RC522] initialized=");
  Serial.println(allReady ? "all-ready" : "partial-or-failed");
}

void releaseCard(ReaderSlot& slot) {
  slot.reader.PICC_HaltA();
  slot.reader.PCD_StopCrypto1();
}

bool shouldThrottleReader(ReaderSlot& slot) {
  return millis() - slot.lastScanAt < SCAN_COOLDOWN_MS;
}

bool readCardUid(ReaderSlot& slot, String& uid) {
  if (!slot.reader.PICC_IsNewCardPresent()) {
    return false;
  }

  if (!slot.reader.PICC_ReadCardSerial()) {
    return false;
  }

  uid = uidToString(slot.reader.uid.uidByte, slot.reader.uid.size);
  return uid.length() > 0;
}

void printDiagSnapshot() {
  Serial.print("[DIAG] wifi_status=");
  Serial.print((int)WiFi.status());
  Serial.print(" ip=");
  Serial.print(WiFi.localIP());
  Serial.print(" api_port=");
  Serial.print(activeApiPort);
  Serial.print(" cloud=");
  if (cloudStatus == CLOUD_CONNECTING) {
    Serial.print("connecting");
  } else if (cloudStatus == CLOUD_ONLINE) {
    Serial.print("online");
  } else {
    Serial.print("offline");
  }
  for (int i = 0; i < READER_COUNT; i++) {
    Serial.print(" ");
    Serial.print(readers[i].sensorName);
    Serial.print("=");
    Serial.print(readers[i].ready ? "ok" : "fail");
  }
  Serial.println();
}

bool readAndProcess(ReaderSlot& slot) {
  if (!slot.ready) {
    return false;
  }

  String uid = "";
  if (!readCardUid(slot, uid)) {
    return false;
  }

  releaseCard(slot);

  if (shouldThrottleReader(slot)) {
    return true;
  }

  String response = sendScan(uid, slot.actionName, slot.sensorName);

  Serial.print("[SCAN] UID=");
  Serial.print(uid);
  Serial.print(" sensor=");
  Serial.print(slot.sensorName);
  Serial.print(" action=");
  Serial.print(slot.actionName);
  Serial.print(" response=");
  Serial.println(response);

  if (response.indexOf("orange_4s") >= 0 || response.indexOf("pending_registration") >= 0) {
    holdOrangePending();
  } else if (response.indexOf("green_2s") >= 0 || response.indexOf("submitted") >= 0) {
    pulseGreenSuccess();
  } else if (response.indexOf("duplicate") >= 0) {
    applyCloudLedBaseline();
  } else {
    setInternalLedRed();
    delay(1000);
    applyCloudLedBaseline();
  }

  slot.lastScanAt = millis();
  return true;
}

void setup() {
  Serial.begin(115200);
  delay(200);

  startupLedTest();

  SPI.begin(RFID_SCK_PIN, RFID_MISO_PIN, RFID_MOSI_PIN, RFID_SENSOR_1_SS_PIN);
  pinMode(RFID_SENSOR_1_SS_PIN, OUTPUT);
  pinMode(RFID_SENSOR_2_SS_PIN, OUTPUT);
  digitalWrite(RFID_SENSOR_1_SS_PIN, HIGH);
  digitalWrite(RFID_SENSOR_2_SS_PIN, HIGH);

  attemptCloudHandshake();
}

void loop() {
  if (millis() - lastDiagPrint > DIAG_PRINT_MS) {
    lastDiagPrint = millis();
    printDiagSnapshot();
  }

  if (anyReaderNotReady() && millis() - lastReaderRetry > READER_RETRY_MS) {
    lastReaderRetry = millis();
    initReaderIfNeeded();
  }

  if (cloudStatus == CLOUD_ONLINE && WiFi.status() != WL_CONNECTED) {
    Serial.println("[NET] Wi-Fi lost while online.");
    activeApiPort = 0;
    setCloudOffline();
    nextCloudAttemptAt = millis() + CLOUD_RETRY_MS;
  }

  if (cloudStatus == CLOUD_ONLINE && millis() - lastHeartbeat > HEARTBEAT_MS) {
    if (sendHeartbeat()) {
      lastHeartbeat = millis();
    } else {
      setCloudOffline();
      nextCloudAttemptAt = millis() + CLOUD_RETRY_MS;
    }
  }

  if (cloudStatus != CLOUD_ONLINE && (nextCloudAttemptAt == 0 || (long)(millis() - nextCloudAttemptAt) >= 0)) {
    attemptCloudHandshake();
  }

  if (canProcessCardReads()) {
    for (int i = 0; i < READER_COUNT; i++) {
      readAndProcess(readers[i]);
    }
  }

  updateStatusLed();
  restartIfOfflineTooLong();

  delay(20);
}
