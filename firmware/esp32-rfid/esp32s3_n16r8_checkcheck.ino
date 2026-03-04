#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <SPI.h>
#include <Adafruit_PN532.h>
#include <Keypad.h>
#include <ctype.h>
#include "secrets.h"

// ======= CONFIG REDE =======
const char* WIFI_SSID = SECRET_WIFI_SSID;
const char* WIFI_PASSWORD = SECRET_WIFI_PASSWORD;
const char* API_SCAN_URL = SECRET_API_SCAN_URL;
const char* API_CHECK_URL = SECRET_API_CHECK_URL;
const char* DEVICE_API_KEY = SECRET_DEVICE_API_KEY;
const char* DEVICE_ID = SECRET_DEVICE_ID;

// ======= PINOS =======
const int LED_READY = 4;    // amarelo
const int LED_SUCCESS = 5;  // verde
const int LED_ERROR = 6;    // vermelho
const int BUZZER_PIN = 7;

// Keypad 4x3 (numerico): 1..9, *, 0, #
const byte KEYPAD_ROWS = 4;
const byte KEYPAD_COLS = 3;
byte keypadRowPins[KEYPAD_ROWS] = {8, 9, 14, 15};
byte keypadColPins[KEYPAD_COLS] = {17, 18, 21};
char keypadMap[KEYPAD_ROWS][KEYPAD_COLS] = {
  {'1', '2', '3'},
  {'4', '5', '6'},
  {'7', '8', '9'},
  {'*', '0', '#'}
};
Keypad keypad = Keypad(makeKeymap(keypadMap), keypadRowPins, keypadColPins, KEYPAD_ROWS, KEYPAD_COLS);

// SPI mapeado para ESP32-S3 N16R8 neste projeto
const int SPI_SCK = 12;
const int SPI_MISO = 13;
const int SPI_MOSI = 11;

const int RFID1_SS = 10; // ENTRY

const bool USE_TWO_READERS = true;
const int RFID2_SS = 16; // EXIT

Adafruit_PN532 readerEntry(RFID1_SS);
Adafruit_PN532 readerExit(RFID2_SS);
WiFiClient plainClient;
WiFiClientSecure secureClient;

unsigned long lastScanMillis = 0;
const unsigned long scanCooldownMs = 1200;
const unsigned long keypadMatriculaTimeoutMs = 25000;

String uidToString(uint8_t* uid, uint8_t uidLength) {
  String out = "";
  for (uint8_t i = 0; i < uidLength; i++) {
    if (uid[i] < 0x10) out += "0";
    out += String(uid[i], HEX);
    if (i < uidLength - 1) out += " ";
  }
  out.toUpperCase();
  return out;
}

void beepTone(int frequency, int durationMs) {
  ledcAttach(BUZZER_PIN, frequency, 8);
  delay(durationMs);
  ledcDetach(BUZZER_PIN);
}

void successSignal() {
  digitalWrite(LED_SUCCESS, HIGH);
  beepTone(2200, 120);
  delay(110);
  beepTone(2200, 120);
  delay(770);
  digitalWrite(LED_SUCCESS, LOW);
}

void errorSignal() {
  digitalWrite(LED_ERROR, HIGH);
  beepTone(300, 600);
  delay(400);
  digitalWrite(LED_ERROR, LOW);
}

bool beginHttp(HTTPClient& http, const String& targetUrl) {
  bool started = false;
  if (targetUrl.startsWith("https://")) {
    if (SECRET_TLS_INSECURE) {
      secureClient.setInsecure();
    }
    started = http.begin(secureClient, targetUrl);
  } else {
    started = http.begin(plainClient, targetUrl);
  }
  return started;
}

bool checkCardRegistered(const String& uid) {
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }

  HTTPClient http;
  String apiUrl = String(API_CHECK_URL);
  bool started = beginHttp(http, apiUrl);
  if (!started) {
    http.end();
    return false;
  }

  http.addHeader("Content-Type", "application/json");
  http.addHeader("x-device-key", DEVICE_API_KEY);

  String body = "{\"rfidUid\":\"" + uid + "\"}";

  int code = http.POST(body);
  if (code < 200 || code >= 300) {
    http.end();
    return false;
  }

  String response = http.getString();
  http.end();
  return response.indexOf("\"exists\":true") >= 0;
}

String readMatriculaFromKeypad() {
  Serial.println("Cartao nao cadastrado. Digite matricula no keypad (7 a 10 digitos) e confirme com # ou *.");
  unsigned long startedAt = millis();
  String typed = "";

  while (millis() - startedAt < keypadMatriculaTimeoutMs) {
    char key = keypad.getKey();
    if (!key) {
      delay(20);
      continue;
    }

    if (key == '#' || key == '*') {
      if (typed.length() >= 7 && typed.length() <= 10) {
        return typed;
      }
      typed = "";
      continue;
    }

    if (isdigit((unsigned char)key) && typed.length() < 10) {
      typed += key;
    }
  }

  return "";
}

bool sendScan(const String& uid, bool entrada, const String& matricula, const String& readerId) {
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }

  HTTPClient http;
  String apiUrl = String(API_SCAN_URL);
  bool started = beginHttp(http, apiUrl);
  if (!started) {
    http.end();
    return false;
  }

  http.addHeader("Content-Type", "application/json");
  http.addHeader("x-device-key", DEVICE_API_KEY);

  String body = "{";
  body += "\"rfidUid\":\"" + uid + "\",";
  body += "\"entrada\":" + String(entrada ? "true" : "false") + ",";
  body += "\"readerId\":\"" + readerId + "\",";
  body += "\"deviceId\":\"" + String(DEVICE_ID) + "\"";
  if (matricula.length() > 0) {
    body += ",\"matricula\":\"" + matricula + "\"";
  }
  body += "}";

  int code = http.POST(body);
  http.end();
  return code >= 200 && code < 300;
}

bool tryRead(Adafruit_PN532& reader, const String& readerId) {
  uint8_t uidBytes[7] = {0};
  uint8_t uidLength = 0;
  bool detected = reader.readPassiveTargetID(PN532_MIFARE_ISO14443A, uidBytes, &uidLength, 60);
  if (!detected || uidLength == 0) {
    return false;
  }

  unsigned long now = millis();
  if (now - lastScanMillis < scanCooldownMs) {
    return false;
  }

  digitalWrite(LED_READY, LOW);
  String uid = uidToString(uidBytes, uidLength);
  bool entrada = readerId == "ENTRY";
  bool isRegistered = checkCardRegistered(uid);
  String matricula = "";

  if (!isRegistered) {
    matricula = readMatriculaFromKeypad();
    if (matricula.length() < 7 || matricula.length() > 10) {
      errorSignal();
      digitalWrite(LED_READY, HIGH);
      lastScanMillis = millis();
      return true;
    }
  }

  bool ok = sendScan(uid, entrada, matricula, readerId);

  if (ok) {
    successSignal();
  } else {
    errorSignal();
  }

  digitalWrite(LED_READY, HIGH);
  lastScanMillis = millis();
  return true;
}

bool initReader(Adafruit_PN532& reader) {
  reader.begin();
  uint32_t versionData = reader.getFirmwareVersion();
  if (!versionData) {
    return false;
  }
  reader.SAMConfig();
  return true;
}

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 20000) {
    delay(300);
  }
}

void setup() {
  Serial.begin(115200);

  pinMode(LED_READY, OUTPUT);
  pinMode(LED_SUCCESS, OUTPUT);
  pinMode(LED_ERROR, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  digitalWrite(LED_READY, LOW);
  digitalWrite(LED_SUCCESS, LOW);
  digitalWrite(LED_ERROR, LOW);

  SPI.begin(SPI_SCK, SPI_MISO, SPI_MOSI);

  bool entryOk = initReader(readerEntry);
  bool exitOk = true;
  if (USE_TWO_READERS) {
    exitOk = initReader(readerExit);
  }

  connectWiFi();

  if (entryOk && exitOk) {
    digitalWrite(LED_READY, HIGH);
  } else {
    errorSignal();
    digitalWrite(LED_READY, HIGH);
  }
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  if (tryRead(readerEntry, "ENTRY")) {
    return;
  }

  if (USE_TWO_READERS) {
    if (tryRead(readerExit, "EXIT")) {
      return;
    }
  }

  delay(30);
}
