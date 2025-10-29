#include <GyverBME280.h>
GyverBME280 bme;
GyverBME280 bme1;

unsigned long lastReadTime = 0;
unsigned long lastMasterActivity = 0;
const unsigned long READ_INTERVAL = 1000;
const unsigned long CONNECTION_TIMEOUT = 3000; // 3 секунды таймаут соединения
const String HANDSHAKE_REQUEST = "HANDSHAKE_REQ";
const String HANDSHAKE_RESPONSE = "HANDSHAKE_ACK";

bool connectionActive = false;

void setup() {
  Serial.begin(115200);
  
  // Даем время на инициализацию
  delay(2000);
  
  // Инициализация датчиков
  if (!bme.begin(0x76)) {
    Serial.println("Sensor:0x76;Status:Error;");
  } else {
    Serial.println("Sensor:0x76;Status:OK;");
  }
  
  if (!bme1.begin(0x77)) {
    Serial.println("Sensor:0x77;Status:Error;");
  } else {
    Serial.println("Sensor:0x77;Status:OK;");
  }
  
  Serial.println("ARDUINO_READY");
  lastMasterActivity = millis(); // Сбрасываем таймер при запуске
}

void loop() {
  // Проверяем не разорвано ли соединение
  if (connectionActive && millis() - lastMasterActivity > CONNECTION_TIMEOUT) {
    connectionActive = false;
    Serial.println("CONNECTION_LOST"); // Для диагностики
  }
  
  // Ждем запрос от Python
  if (Serial.available() > 0) {
    String request = Serial.readStringUntil('\n');
    request.trim();
    
    // Обновляем время последней активности
    lastMasterActivity = millis();
    
    if (request == HANDSHAKE_REQUEST) {
      // Отправляем подтверждение
      Serial.println(HANDSHAKE_RESPONSE);
      connectionActive = true;
      delay(10);
    }
    else if (request == "DATA_REQUEST") {
      // Отправляем данные датчиков
      sendSensorData();
    }
    else if (request == "PING") {
      // Ответ на ping (если вдруг добавите)
      Serial.println("PONG");
    }
  }
  
  // Автономная отправка только при активном соединении
  if (connectionActive && millis() - lastReadTime >= READ_INTERVAL) {
    lastReadTime = millis();
    sendSensorData();
  }
  
  // Если соединение не активно, можно делать что-то еще
  // Например, мигать светодиодом или отправлять статус
  if (!connectionActive) {
    // Мигаем встроенным светодиодом (пин 13) если соединение потеряно
    static unsigned long lastBlink = 0;
    if (millis() - lastBlink > 1000) {
      lastBlink = millis();
      digitalWrite(13, !digitalRead(13)); // Мигаем LED
    }
    
    // Периодически отправляем статус готовности
    static unsigned long lastStatusTime = 0;
    if (millis() - lastStatusTime > 5000) { // Каждые 5 секунд
      lastStatusTime = millis();
      Serial.println("ARDUINO_WAITING");
    }
  } else {
    digitalWrite(13, HIGH); // LED включен при активном соединении
  }
}

void sendSensorData() {
  String data76 = "Sensor:0x76;Temperature:" + String(bme.readTemperature(), 2) + 
                 ";Pressure:" + String(bme.readPressure(), 2) + ";";
  String data77 = "Sensor:0x77;Temperature:" + String(bme1.readTemperature(), 2) + 
                 ";Pressure:" + String(bme1.readPressure(), 2) + ";";
  Serial.println(data76 + data77);
}