#include <WiFi.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <Wire.h>
#include <Adafruit_PN532.h>

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

const char* WIFI_SSID = "P80_WiFi";
const char* WIFI_PASSWORD = "Petrobras@80";
const char* API_HOST = "157.230.35.21";
const char* DEVICE_ID = "ESP32-S3-01";
const char* SHARED_KEY = "gyb2YCkwhDFkhhYQQC6W80BafOf9YsTr";

const int API_PORTS[] = {8000, 8001};
const int API_PORTS_COUNT = 2;

const int SPI_SCK = 12;
const int SPI_MISO = 13;
const int SPI_MOSI = 11;
const int PN532_SS = 9;

const int I2C_SDA = 8;
const int I2C_SCL = 9;
const int PN532_IRQ = -1;
const int PN532_RESET = -1;

Adafruit_PN532 rfidReaderSpi(PN532_SS);
Adafruit_PN532 rfidReaderI2c(PN532_IRQ, PN532_RESET);
Adafruit_PN532* activeReader = nullptr;

enum ReaderBus {
  BUS_NONE,
  BUS_I2C,
  BUS_SPI
};

ReaderBus activeReaderBus = BUS_NONE;

unsigned long lastHeartbeat = 0;
unsigned long lastScan = 0;
unsigned long lastWifiAttempt = 0;
unsigned long lastReaderRetry = 0;

const unsigned long HEARTBEAT_MS = 180000;
const unsigned long SCAN_COOLDOWN_MS = 1200;
const unsigned long WIFI_RETRY_MS = 10000;
const unsigned long READER_RETRY_MS = 5000;

bool readerReady = false;
int activeApiPort = 0;

unsigned long lastDiagPrint = 0;
const unsigned long DIAG_PRINT_MS = 10000;

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

void blinkInternalGreenConnected() {
  for (int i = 0; i < 3; i++) {
    setInternalLedGreen();
    delay(100);
    setInternalLedOff();
    delay(100);
  }
}

void ledsOff() {
  setInternalLedOff();
}

void setWhiteOnline() {
  setInternalLedWhite();
}

void setRedOffline() {
  setInternalLedRed();
}

void pulseGreenSuccess() {
  setInternalLedGreen();
  delay(2000);
  setWhiteOnline();
}

void blinkYellowPending() {
  for (int i = 0; i < 2; i++) {
    setInternalLedYellow();
    delay(250);
    setInternalLedOff();
    delay(250);
  }
  setWhiteOnline();
}

void startupLedTest() {
  // Keep LED off at boot; status colors are shown only by runtime state.
  setInternalLedOff();
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

String sendScan(const String& uid) {
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

  String requestId = String(DEVICE_ID) + "-" + String(millis()) + "-" + uid;

  String body = "{";
  body += "\"rfid\":\"" + uid + "\",";
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

bool initReader(Adafruit_PN532& reader, const char* modeName) {
  reader.begin();
  uint32_t versionData = reader.getFirmwareVersion();
  if (!versionData) {
    Serial.print("[PN532] ");
    Serial.print(modeName);
    Serial.println(" getFirmwareVersion=0x00000000 (sem resposta no barramento)");
    return false;
  }
  Serial.print("[PN532] ");
  Serial.print(modeName);
  Serial.print(" getFirmwareVersion=0x");
  Serial.println(versionData, HEX);
  reader.SAMConfig();
  return true;
}

bool initReaderI2C() {
  Wire.begin(I2C_SDA, I2C_SCL);
  delay(20);
  if (initReader(rfidReaderI2c, "I2C")) {
    activeReader = &rfidReaderI2c;
    activeReaderBus = BUS_I2C;
    return true;
  }
  return false;
}

bool initReaderSPI() {
  SPI.begin(SPI_SCK, SPI_MISO, SPI_MOSI);
  delay(20);
  if (initReader(rfidReaderSpi, "SPI")) {
    activeReader = &rfidReaderSpi;
    activeReaderBus = BUS_SPI;
    return true;
  }
  return false;
}

const char* currentReaderBusName() {
  if (activeReaderBus == BUS_I2C) {
    return "i2c";
  }
  if (activeReaderBus == BUS_SPI) {
    return "spi";
  }
  return "none";
}

void initReaderIfNeeded() {
  if (!readerReady) {
    readerReady = initReaderI2C();
    if (!readerReady) {
      readerReady = initReaderSPI();
    }
    Serial.print("[PN532] reader=");
    Serial.print(readerReady ? "ok" : "fail");
    Serial.print(" bus=");
    Serial.println(currentReaderBusName());
  }
}

void printDiagSnapshot() {
  Serial.print("[DIAG] wifi_status=");
  Serial.print((int)WiFi.status());
  Serial.print(" ip=");
  Serial.print(WiFi.localIP());
  Serial.print(" api_port=");
  Serial.print(activeApiPort);
  Serial.print(" reader=");
  Serial.print(readerReady ? "ok" : "fail");
  Serial.print(" bus=");
  Serial.println(currentReaderBusName());
}

bool readAndProcess(Adafruit_PN532& reader) {
  uint8_t uidBytes[7] = {0};
  uint8_t uidLength = 0;
  bool detected = reader.readPassiveTargetID(PN532_MIFARE_ISO14443A, uidBytes, &uidLength, 60);
  if (!detected || uidLength == 0) {
    return false;
  }

  if (millis() - lastScan < SCAN_COOLDOWN_MS) {
    return true;
  }

  String uid = uidToString(uidBytes, uidLength);
  String response = sendScan(uid);

  Serial.print("[SCAN] UID=");
  Serial.print(uid);
  Serial.print(" response=");
  Serial.println(response);

  if (response.indexOf("pending_registration") >= 0) {
    blinkYellowPending();
  } else if (response.indexOf("green_2s") >= 0 || response.indexOf("submitted") >= 0) {
    pulseGreenSuccess();
  } else if (response.indexOf("duplicate") >= 0) {
    setWhiteOnline();
  } else {
    setRedOffline();
    delay(1000);
    setWhiteOnline();
  }

  lastScan = millis();
  return true;
}

void connectWifiAndSignal() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  setInternalLedYellow();
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
    setRedOffline();
    return;
  }

  blinkInternalGreenConnected();

  if (sendHeartbeat()) {
    Serial.print("[NET] Online. IP: ");
    Serial.println(WiFi.localIP());
    setWhiteOnline();
  } else {
    Serial.println("[NET] Online, but heartbeat failed.");
    setRedOffline();
  }
}

void setup() {
  Serial.begin(115200);
  delay(200);

  startupLedTest();

  initReaderIfNeeded();
  connectWifiAndSignal();
}

void loop() {
  if (millis() - lastDiagPrint > DIAG_PRINT_MS) {
    lastDiagPrint = millis();
    printDiagSnapshot();
  }

  if (!readerReady && millis() - lastReaderRetry > READER_RETRY_MS) {
    lastReaderRetry = millis();
    initReaderIfNeeded();
  }

  if (millis() - lastHeartbeat > HEARTBEAT_MS) {
    lastHeartbeat = millis();
    if (WiFi.status() == WL_CONNECTED && sendHeartbeat()) {
      setWhiteOnline();
    } else {
      setRedOffline();
    }
  }

  if (WiFi.status() != WL_CONNECTED && millis() - lastWifiAttempt > WIFI_RETRY_MS) {
    lastWifiAttempt = millis();
    connectWifiAndSignal();
  }

  if (readerReady && activeReader != nullptr) {
    readAndProcess(*activeReader);
  }

  delay(20);
}
