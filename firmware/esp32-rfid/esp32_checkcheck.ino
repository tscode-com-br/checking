#include <WiFi.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <MFRC522.h>

// ======= CONFIG REDE =======
const char* WIFI_SSID = "SEU_WIFI";
const char* WIFI_PASSWORD = "SUA_SENHA";
const char* API_URL = "http://192.168.0.10:3000/api/scan";
const char* DEVICE_API_KEY = "troque-esta-chave-dispositivo";
const char* DEVICE_ID = "ESP32-PORTARIA-01";

// ======= PINOS =======
const int LED_READY = 25;   // amarelo
const int LED_SUCCESS = 26; // verde
const int LED_ERROR = 27;   // vermelho
const int BUZZER_PIN = 14;

// SPI padrão ESP32: SCK=18, MISO=19, MOSI=23
const int RFID1_SS = 5;
const int RFID1_RST = 22;

const bool USE_TWO_READERS = true;
const int RFID2_SS = 21;
const int RFID2_RST = 4;

MFRC522 readerEntry(RFID1_SS, RFID1_RST);
MFRC522 readerExit(RFID2_SS, RFID2_RST);

unsigned long lastScanMillis = 0;
const unsigned long scanCooldownMs = 1200;

String uidToString(MFRC522::Uid* uid) {
  String out = "";
  for (byte i = 0; i < uid->size; i++) {
    if (uid->uidByte[i] < 0x10) out += "0";
    out += String(uid->uidByte[i], HEX);
    if (i < uid->size - 1) out += " ";
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

bool sendScan(const String& uid, const String& readerId) {
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }

  HTTPClient http;
  http.begin(API_URL);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("x-device-key", DEVICE_API_KEY);

  String body = "{";
  body += "\"rfidUid\":\"" + uid + "\",";
  body += "\"readerId\":\"" + readerId + "\",";
  body += "\"deviceId\":\"" + String(DEVICE_ID) + "\"";
  body += "}";

  int code = http.POST(body);
  http.end();
  return code >= 200 && code < 300;
}

bool tryRead(MFRC522& reader, String readerId) {
  if (!reader.PICC_IsNewCardPresent() || !reader.PICC_ReadCardSerial()) {
    return false;
  }

  unsigned long now = millis();
  if (now - lastScanMillis < scanCooldownMs) {
    reader.PICC_HaltA();
    reader.PCD_StopCrypto1();
    return false;
  }

  digitalWrite(LED_READY, LOW);
  String uid = uidToString(&reader.uid);
  bool ok = sendScan(uid, readerId);

  if (ok) {
    successSignal();
  } else {
    errorSignal();
  }

  digitalWrite(LED_READY, HIGH);
  lastScanMillis = millis();

  reader.PICC_HaltA();
  reader.PCD_StopCrypto1();
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
  pinMode(LED_READY, OUTPUT);
  pinMode(LED_SUCCESS, OUTPUT);
  pinMode(LED_ERROR, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  digitalWrite(LED_READY, LOW);
  digitalWrite(LED_SUCCESS, LOW);
  digitalWrite(LED_ERROR, LOW);

  SPI.begin();
  readerEntry.PCD_Init();
  if (USE_TWO_READERS) {
    readerExit.PCD_Init();
  }

  connectWiFi();
  digitalWrite(LED_READY, HIGH);
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
