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
  String lastUid;
  unsigned long lastUidSeenAt;

  ReaderSlot(byte ssPinValue, byte rstPinValue, const char* sensorNameValue, const char* actionNameValue)
      : reader(ssPinValue, rstPinValue), sensorName(sensorNameValue), actionName(actionNameValue), ssPin(ssPinValue), ready(false), lastScanAt(0), lastUid(""), lastUidSeenAt(0) {}
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
const unsigned long SAME_CARD_SUPPRESSION_MS = 3000;
const unsigned long CLOUD_RETRY_MS = 30000;
const unsigned long OFFLINE_RESTART_MS = 30000;
const unsigned long READER_RETRY_MS = 5000;
const uint16_t API_CONNECT_TIMEOUT_MS = 10000;
const uint16_t API_RESPONSE_TIMEOUT_MS = 60000;

int activeApiPort = 0;

unsigned long lastDiagPrint = 0;
const unsigned long DIAG_PRINT_MS = 10000;

enum CloudStatus {
  CLOUD_CONNECTING,
  CLOUD_ONLINE,
  CLOUD_OFFLINE
};

CloudStatus cloudStatus = CLOUD_CONNECTING;

const unsigned long CONNECTING_BLINK_COUNT = 3;
const unsigned long CONNECTING_BLINK_ON_MS = 40;
const unsigned long CONNECTING_PATTERN_MS = 1500;
const unsigned long ONLINE_BLINK_COUNT = 1;
const unsigned long ONLINE_BLINK_ON_MS = 20;
const unsigned long ONLINE_PATTERN_MS = 2000;
const unsigned long OFFLINE_BLINK_COUNT = 1;
const unsigned long OFFLINE_BLINK_ON_MS = 40;
const unsigned long OFFLINE_PATTERN_MS = 2000;
const unsigned long SUCCESS_BLINK_COUNT = 1;
const unsigned long SUCCESS_BLINK_ON_MS = 1000;
const unsigned long SUCCESS_PATTERN_MS = 1000;
const unsigned long LOCAL_UPDATED_BLINK_COUNT = 1;
const unsigned long LOCAL_UPDATED_BLINK_ON_MS = 1000;
const unsigned long LOCAL_UPDATED_PATTERN_MS = 1000;
const unsigned long PENDING_BLINK_COUNT = 3;
const unsigned long PENDING_BLINK_ON_MS = 40;
const unsigned long PENDING_PATTERN_MS = 1500;
const unsigned long BUSINESS_RULE_BLINK_COUNT = 3;
const unsigned long BUSINESS_RULE_BLINK_ON_MS = 40;
const unsigned long BUSINESS_RULE_PATTERN_MS = 1500;
const unsigned long FAILURE_HOLD_MS = 1500;
const unsigned long FALLBACK_BLINK_COUNT = 2;
const unsigned long FALLBACK_BLINK_ON_MS = 40;
const unsigned long FALLBACK_PATTERN_MS = 1000;

void (*activeStatusLedSetter)() = nullptr;
unsigned long activeStatusBlinkCount = 0;
unsigned long activeStatusOnMs = 0;
unsigned long activeStatusTotalMs = 0;
unsigned long activeStatusSlotMs = 0;
unsigned long statusCycleStartedAt = 0;
unsigned long statusPulseEndsAt = 0;
unsigned long nextStatusPulseAt = 0;
unsigned long nextStatusPulseIndex = 0;
bool statusLedIsOn = false;

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

void setInternalLedBlue() {
#ifdef RGB_BUILTIN
  neopixelWrite(RGB_BUILTIN, 0, 0, 255);
#endif
}

void setInternalLedRed() {
#ifdef RGB_BUILTIN
  neopixelWrite(RGB_BUILTIN, 255, 0, 0);
#endif
}

void runLedBlinkPattern(void (*ledSetter)(), unsigned long blinkCount, unsigned long onMs, unsigned long totalMs) {
  if (blinkCount == 0 || ledSetter == nullptr) {
    return;
  }

  unsigned long slotMs = totalMs / blinkCount;
  if (slotMs < onMs) {
    slotMs = onMs;
  }

  unsigned long offMs = slotMs - onMs;
  for (unsigned long i = 0; i < blinkCount; i++) {
    ledSetter();
    delay(onMs);
    setInternalLedOff();
    if (offMs > 0) {
      delay(offMs);
    }
  }
}

void resetStatusBlink() {
  activeStatusLedSetter = nullptr;
  activeStatusBlinkCount = 0;
  activeStatusOnMs = 0;
  activeStatusTotalMs = 0;
  activeStatusSlotMs = 0;
  statusCycleStartedAt = 0;
  statusPulseEndsAt = 0;
  nextStatusPulseAt = 0;
  nextStatusPulseIndex = 0;
  statusLedIsOn = false;
}

void getCloudStatusPattern(void (**ledSetter)(), unsigned long& blinkCount, unsigned long& onMs, unsigned long& totalMs) {
  if (cloudStatus == CLOUD_CONNECTING) {
    *ledSetter = setInternalLedBlue;
    blinkCount = CONNECTING_BLINK_COUNT;
    onMs = CONNECTING_BLINK_ON_MS;
    totalMs = CONNECTING_PATTERN_MS;
    return;
  }

  if (cloudStatus == CLOUD_OFFLINE) {
    *ledSetter = setInternalLedRed;
    blinkCount = OFFLINE_BLINK_COUNT;
    onMs = OFFLINE_BLINK_ON_MS;
    totalMs = OFFLINE_PATTERN_MS;
    return;
  }

  *ledSetter = setInternalLedGreen;
  blinkCount = ONLINE_BLINK_COUNT;
  onMs = ONLINE_BLINK_ON_MS;
  totalMs = ONLINE_PATTERN_MS;
}

void tickCloudStatusLed() {
  unsigned long now = millis();
  unsigned long blinkCount = 0;
  unsigned long onMs = 0;
  unsigned long totalMs = 0;
  void (*statusLedSetter)() = nullptr;
  getCloudStatusPattern(&statusLedSetter, blinkCount, onMs, totalMs);

  if (statusLedSetter == nullptr || blinkCount == 0 || totalMs == 0) {
    resetStatusBlink();
    setInternalLedOff();
    return;
  }

  unsigned long slotMs = totalMs / blinkCount;
  if (slotMs < onMs) {
    slotMs = onMs;
  }

  bool patternChanged = activeStatusLedSetter != statusLedSetter
    || activeStatusBlinkCount != blinkCount
    || activeStatusOnMs != onMs
    || activeStatusTotalMs != totalMs;

  if (patternChanged || statusCycleStartedAt == 0) {
    activeStatusLedSetter = statusLedSetter;
    activeStatusBlinkCount = blinkCount;
    activeStatusOnMs = onMs;
    activeStatusTotalMs = totalMs;
    activeStatusSlotMs = slotMs;
    statusCycleStartedAt = now;
    statusPulseEndsAt = now + onMs;
    nextStatusPulseIndex = 1;
    nextStatusPulseAt = statusCycleStartedAt + activeStatusSlotMs;
    statusLedIsOn = true;
    activeStatusLedSetter();
    return;
  }

  if (statusLedIsOn && (long)(now - statusPulseEndsAt) >= 0) {
    statusLedIsOn = false;
    setInternalLedOff();
  }

  while ((long)(now - (statusCycleStartedAt + activeStatusTotalMs)) >= 0) {
    statusCycleStartedAt += activeStatusTotalMs;
    nextStatusPulseIndex = 0;
    nextStatusPulseAt = statusCycleStartedAt;
  }

  if (!statusLedIsOn && nextStatusPulseIndex < activeStatusBlinkCount && (long)(now - nextStatusPulseAt) >= 0) {
    statusPulseEndsAt = now + activeStatusOnMs;
    nextStatusPulseIndex++;
    nextStatusPulseAt = statusCycleStartedAt + (nextStatusPulseIndex * activeStatusSlotMs);
    statusLedIsOn = true;
    activeStatusLedSetter();
    return;
  }

  if (statusLedIsOn) {
    activeStatusLedSetter();
    return;
  }

  setInternalLedOff();
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
  resetStatusBlink();
  setInternalLedOff();
  tickCloudStatusLed();
}

void resumeOnlineIdleState() {
  if (cloudStatus != CLOUD_ONLINE) {
    applyCloudLedBaseline();
    return;
  }

  resetStatusBlink();
  setInternalLedOff();
}

void pulseGreenSuccess() {
  runLedBlinkPattern(setInternalLedGreen, SUCCESS_BLINK_COUNT, SUCCESS_BLINK_ON_MS, SUCCESS_PATTERN_MS);
  resumeOnlineIdleState();
}

void holdOrangePending() {
  runLedBlinkPattern(setInternalLedOrange, PENDING_BLINK_COUNT, PENDING_BLINK_ON_MS, PENDING_PATTERN_MS);
  resumeOnlineIdleState();
}

void holdRedTwoSeconds() {
  runLedBlinkPattern(setInternalLedRed, BUSINESS_RULE_BLINK_COUNT, BUSINESS_RULE_BLINK_ON_MS, BUSINESS_RULE_PATTERN_MS);
  resumeOnlineIdleState();
}

void blinkGreenLocationUpdated() {
  runLedBlinkPattern(setInternalLedGreen, LOCAL_UPDATED_BLINK_COUNT, LOCAL_UPDATED_BLINK_ON_MS, LOCAL_UPDATED_PATTERN_MS);
  resumeOnlineIdleState();
}

void blinkRedFailurePattern() {
  setInternalLedRed();
  delay(FAILURE_HOLD_MS);
  resumeOnlineIdleState();
}

void startupLedTest() {
  applyCloudLedBaseline();
}

void setCloudConnecting() {
  cloudStatus = CLOUD_CONNECTING;
  applyCloudLedBaseline();
}

void setCloudOnline() {
  cloudStatus = CLOUD_ONLINE;
  offlineSince = 0;
  resetStatusBlink();
  applyCloudLedBaseline();
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
  tickCloudStatusLed();
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
  http.setConnectTimeout(API_CONNECT_TIMEOUT_MS);
  http.setTimeout(API_RESPONSE_TIMEOUT_MS);

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
    tickCloudStatusLed();
    delay(20);
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
  http.setConnectTimeout(API_CONNECT_TIMEOUT_MS);
  http.setTimeout(API_RESPONSE_TIMEOUT_MS);

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
    Serial.print("[SCAN] HTTP error code=");
    Serial.print(code);
    Serial.print(" body=");
    Serial.println(response);
    if (code <= 0) {
      activeApiPort = 0;
    }
    return String("http_error:") + String(code) + ":" + response;
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

bool shouldSuppressRepeatedUid(ReaderSlot& slot, const String& uid) {
  unsigned long now = millis();
  bool suppress = slot.lastUid == uid && (now - slot.lastUidSeenAt) < SAME_CARD_SUPPRESSION_MS;

  slot.lastUid = uid;
  slot.lastUidSeenAt = now;
  return suppress;
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

String extractJsonStringValue(const String& payload, const char* key) {
  String marker = String("\"") + key + "\":";
  int markerIndex = payload.indexOf(marker);
  if (markerIndex < 0) {
    return "";
  }

  int valueStart = markerIndex + marker.length();
  while (valueStart < payload.length() && (payload[valueStart] == ' ' || payload[valueStart] == '\t')) {
    valueStart++;
  }

  if (valueStart >= payload.length() || payload[valueStart] != '"') {
    return "";
  }

  valueStart++;
  int valueEnd = valueStart;
  while (valueEnd < payload.length()) {
    if (payload[valueEnd] == '"' && payload[valueEnd - 1] != '\\') {
      break;
    }
    valueEnd++;
  }

  if (valueEnd >= payload.length()) {
    return "";
  }

  return payload.substring(valueStart, valueEnd);
}

void showProcessingLed() {
  resetStatusBlink();
  setInternalLedBlue();
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

  if (shouldSuppressRepeatedUid(slot, uid)) {
    Serial.print("[SCAN] Suppressed repeated UID=");
    Serial.print(uid);
    Serial.print(" sensor=");
    Serial.println(slot.sensorName);
    return true;
  }

  if (shouldThrottleReader(slot)) {
    return true;
  }

  slot.lastScanAt = millis();
  showProcessingLed();
  String response = sendScan(uid, slot.actionName, slot.sensorName);
  String responseLed = extractJsonStringValue(response, "led");
  String responseOutcome = extractJsonStringValue(response, "outcome");

  Serial.print("[SCAN] UID=");
  Serial.print(uid);
  Serial.print(" sensor=");
  Serial.print(slot.sensorName);
  Serial.print(" action=");
  Serial.print(slot.actionName);
  Serial.print(" response=");
  Serial.println(response);
  Serial.print("[SCAN] parsed_led=");
  Serial.print(responseLed.length() > 0 ? responseLed : "-");
  Serial.print(" parsed_outcome=");
  Serial.println(responseOutcome.length() > 0 ? responseOutcome : "-");

  if (responseLed == "orange_4s" || responseOutcome == "pending_registration" || response.indexOf("orange_4s") >= 0 || response.indexOf("pending_registration") >= 0) {
    holdOrangePending();
  } else if (responseLed == "green_1s" || responseLed == "green_2s" || responseOutcome == "submitted" || response.indexOf("green_1s") >= 0 || response.indexOf("green_2s") >= 0 || response.indexOf("submitted") >= 0) {
    pulseGreenSuccess();
  } else if (responseLed == "green_blink_3x_1s" || responseOutcome == "local_updated" || response.indexOf("green_blink_3x_1s") >= 0 || response.indexOf("local_updated") >= 0) {
    blinkGreenLocationUpdated();
  } else if (responseLed == "red_2s" || response.indexOf("red_2s") >= 0) {
    holdRedTwoSeconds();
  } else if (responseLed == "red_blink_5x_1s" || response.indexOf("red_blink_5x_1s") >= 0) {
    blinkRedFailurePattern();
  } else if (responseLed == "white" || responseOutcome == "duplicate" || response.indexOf("duplicate") >= 0 || response.indexOf("\"led\":\"white\"") >= 0) {
    resumeOnlineIdleState();
  } else {
    Serial.println("[SCAN] Unrecognized API response; fallback red_1s activated.");
    runLedBlinkPattern(setInternalLedRed, FALLBACK_BLINK_COUNT, FALLBACK_BLINK_ON_MS, FALLBACK_PATTERN_MS);
    resumeOnlineIdleState();
  }

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
