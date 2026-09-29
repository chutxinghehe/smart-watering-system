/**
 * Smart Watering System - ESP32 Firmware
 * 
 * Hardware Setup:
 * - ESP32 Dev Board
 * - Capacitive Soil Moisture Sensor → GPIO 34 (ADC1_CH6)
 * - DHT22 Temperature/Humidity Sensor → GPIO 4
 * - Relay Module (active LOW) → GPIO 5
 * - 5V Water Pump connected to Relay
 * 
 * Wiring:
 * Soil Sensor:
 *   VCC → 3.3V
 *   GND → GND
 *   AOUT → GPIO 34
 * 
 * DHT22:
 *   VCC → 3.3V
 *   GND → GND
 *   DATA → GPIO 4 (với pull-up resistor 10kΩ)
 * 
 * Relay:
 *   VCC → 5V
 *   GND → GND
 *   IN → GPIO 5
 *   NO/COM → Pump control
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <DHT.h>

// ============= CONFIG =============

// Wi-Fi credentials (THAY ĐỔI CHO PHÙNG HỢP MẠNG CỦA BẠN)
const char* WIFI_SSID = "Nha 26C T3";      // Tên Wi-Fi
const char* WIFI_PASSWORD = "68686868";  // Mật khẩu Wi-Fi

// Server config (THAY ĐỔI IP CỦA PC CHẠY FLASK)
const char* SERVER_IP = "192.168.1.16";  // IP của PC chạy Flask server
const int SERVER_PORT = 5000;

// Pin definitions
#define SOIL_SENSOR_PIN 34   // ADC pin cho soil moisture
#define DHT_PIN 4            // DHT22 data pin
#define RELAY_PIN 5          // Relay control pin (active LOW)

// DHT sensor type
#define DHT_TYPE DHT22

// Timing
const unsigned long SENSOR_READ_INTERVAL = 30000;  // 30 seconds
const unsigned long WATERING_DURATION = 10000;     // 10 seconds
const unsigned long COOLDOWN_PERIOD = 300000;      // 5 minutes

// Soil moisture calibration (HIỆU CHỈNH THEO CẢM BIẾN CỦA BẠN)
const int SOIL_DRY_VALUE = 3200;    // Giá trị ADC khi đất khô (không cắm đất)
const int SOIL_WET_VALUE = 1500;    // Giá trị ADC khi đất ẩm (ngâm nước)

// ============= GLOBALS =============

DHT dht(DHT_PIN, DHT_TYPE);

unsigned long lastSensorRead = 0;
unsigned long lastWateringTime = 0;
bool isPumpOn = false;

// Sensor data
float soilMoisture = 0;
float temperature = 0;
float humidity = 0;

// ============= SETUP =============

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n\n========================================");
  Serial.println("🌱 Smart Watering System - ESP32");
  Serial.println("========================================\n");
  
  // Init pins
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, HIGH);  // Relay OFF (active LOW)
  
  pinMode(SOIL_SENSOR_PIN, INPUT);
  
  // Init DHT sensor
  dht.begin();
  Serial.println("✅ DHT22 sensor initialized");
  
  // Connect to Wi-Fi
  connectWiFi();
  
  Serial.println("\n✅ Setup completed!");
  Serial.println("Starting main loop...\n");
}

// ============= MAIN LOOP =============

void loop() {
  // Check Wi-Fi connection
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("⚠️  Wi-Fi disconnected! Reconnecting...");
    connectWiFi();
  }
  
  // Read sensors every interval
  if (millis() - lastSensorRead >= SENSOR_READ_INTERVAL) {
    lastSensorRead = millis();
    
    // Read sensors
    readSensors();
    
    // Send data to server và nhận quyết định AI
    bool shouldWater = sendDataToServer();
    
    // Auto watering (nếu AI suggest và đã qua cooldown)
    if (shouldWater && !isPumpOn) {
      if (millis() - lastWateringTime >= COOLDOWN_PERIOD) {
        Serial.println("🤖 AI suggests watering!");
        waterPlant(10);  // Tưới 10 giây
      } else {
        unsigned long remainingCooldown = (COOLDOWN_PERIOD - (millis() - lastWateringTime)) / 1000;
        Serial.printf("⏳ Cooldown active, wait %lu seconds\n", remainingCooldown);
      }
    }
  }
  
  // Check manual command từ server
  checkManualCommand();
  
  delay(1000);  // Small delay
}

// ============= Wi-Fi =============

void connectWiFi() {
  Serial.printf("📡 Connecting to Wi-Fi: %s\n", WIFI_SSID);
  
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ Wi-Fi connected!");
    Serial.printf("📍 IP Address: %s\n", WiFi.localIP().toString().c_str());
    Serial.printf("📡 Signal strength: %d dBm\n", WiFi.RSSI());
  } else {
    Serial.println("\n❌ Wi-Fi connection failed!");
    Serial.println("⚠️  Check SSID and password in code");
    Serial.println("Retrying in 10 seconds...");
    delay(10000);
    ESP.restart();
  }
}

// ============= SENSORS =============

void readSensors() {
  Serial.println("\n📊 Reading sensors...");
  
  // Read soil moisture
  int rawValue = analogRead(SOIL_SENSOR_PIN);
  
  // Convert to percentage (0-100%)
  // Lower ADC value = more wet, higher = more dry
  soilMoisture = map(rawValue, SOIL_WET_VALUE, SOIL_DRY_VALUE, 100, 0);
  soilMoisture = constrain(soilMoisture, 0, 100);
  
  Serial.printf("   💧 Soil Moisture: %.1f%% (raw: %d)\n", soilMoisture, rawValue);
  
  // Read DHT22
  temperature = dht.readTemperature();
  humidity = dht.readHumidity();
  
  if (isnan(temperature) || isnan(humidity)) {
    Serial.println("   ❌ DHT22 read failed!");
    temperature = 25.0;  // Fallback value
    humidity = 60.0;
  } else {
    Serial.printf("   🌡️  Temperature: %.1f°C\n", temperature);
    Serial.printf("   ☁️  Humidity: %.1f%%\n", humidity);
  }
}

// ============= SERVER COMMUNICATION =============

bool sendDataToServer() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("❌ No Wi-Fi, skipping server send");
    return false;
  }
  
  HTTPClient http;
  
  // Build URL
  String url = String("http://") + SERVER_IP + ":" + SERVER_PORT + "/api/sensor-data";
  
  // Build JSON payload
  StaticJsonDocument<200> doc;
  doc["moisture"] = soilMoisture;
  doc["temperature"] = temperature;
  doc["humidity"] = humidity;
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  Serial.println("\n📤 Sending data to server...");
  Serial.printf("   URL: %s\n", url.c_str());
  Serial.printf("   Payload: %s\n", jsonString.c_str());
  
  // Send POST request
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  int httpCode = http.POST(jsonString);
  
  bool shouldWater = false;
  
  if (httpCode == 200) {
    String response = http.getString();
    Serial.printf("   ✅ Response: %s\n", response.c_str());
    
    // Parse response
    StaticJsonDocument<200> responseDoc;
    DeserializationError error = deserializeJson(responseDoc, response);
    
    if (!error) {
      shouldWater = responseDoc["should_water"];
      float confidence = responseDoc["confidence"];
      
      Serial.printf("   🤖 AI Decision: %s (confidence: %.1f%%)\n", 
                    shouldWater ? "WATER" : "NO WATER", 
                    confidence * 100);
    }
  } else {
    Serial.printf("   ❌ HTTP error: %d\n", httpCode);
    Serial.printf("   Error: %s\n", http.errorToString(httpCode).c_str());
  }
  
  http.end();
  return shouldWater;
}

void checkManualCommand() {
  if (WiFi.status() != WL_CONNECTED) {
    return;
  }
  
  HTTPClient http;
  String url = String("http://") + SERVER_IP + ":" + SERVER_PORT + "/api/command";
  
  http.begin(url);
  int httpCode = http.GET();
  
  if (httpCode == 200) {
    String response = http.getString();
    
    StaticJsonDocument<100> doc;
    DeserializationError error = deserializeJson(doc, response);
    
    if (!error && !doc["command"].isNull()) {
      String command = doc["command"].as<String>();
      
      Serial.printf("\n🎮 Manual command received: %s\n", command.c_str());
      
      if (command == "on") {
        waterPlant(10);
      } else if (command == "off") {
        stopPump();
      }
    }
  }
  
  http.end();
}

// ============= PUMP CONTROL =============

void waterPlant(int durationSeconds) {
  Serial.printf("\n💦 Starting watering for %d seconds...\n", durationSeconds);
  
  digitalWrite(RELAY_PIN, LOW);  // Relay ON (active LOW)
  isPumpOn = true;
  
  delay(durationSeconds * 1000);
  
  digitalWrite(RELAY_PIN, HIGH);  // Relay OFF
  isPumpOn = false;
  
  lastWateringTime = millis();
  
  Serial.println("✅ Watering completed!");
}

void stopPump() {
  if (isPumpOn) {
    digitalWrite(RELAY_PIN, HIGH);  // Relay OFF
    isPumpOn = false;
    Serial.println("🛑 Pump stopped");
  }
}
