#include <SoftwareSerial.h>
#include <LiquidCrystal.h>

LiquidCrystal lcd(8, 9, 4, 5, 6, 7);

const int rxPin = 10;  // Connect to Module TXD
const int txPin = 11;  // Connect to Module RXD (via voltage divider)
const int auxPin = 13;
const int buzzPin = 12;
const int ledPin = 2;

bool pumpRunning = false;

SoftwareSerial loraSerial(rxPin, txPin);

bool waitByte(unsigned long timeoutMs = 100) {
  unsigned long t = millis();
  while (!loraSerial.available()) {
    if (millis() - t > timeoutMs) return false;
  }
  return true;
}

void setup() {
  Serial.begin(9600);
  loraSerial.begin(9600);
  pinMode(auxPin, INPUT);
  pinMode(buzzPin, OUTPUT);

  lcd.begin(16, 2);
  lcd.setCursor(0, 0);
  lcd.print("Depth:    cm");
  lcd.setCursor(0, 1);
  lcd.print("Pct:  %");

}

void loop() {
/*  if (loraSerial.available()) {
    String received = "";

    // Read until newline or buffer exhausted
    while (loraSerial.available()) {
      char c = (char)loraSerial.read();
      received += c;
      delay(2);  // Small gap to let SoftwareSerial buffer fill
    }

    received.trim();

    if (received.length() > 0) {
      Serial.println("RX: " + received);

      // Display on LCD
      lcd.clear();
      lcd.setCursor(0, 0);
      // First 16 chars on line 0
      if (received.length() <= 16) {
        lcd.print(received);
      } else {
        lcd.print(received.substring(0, 16));
        lcd.setCursor(0, 1);
        lcd.print(received.substring(16, 32));
      }
    }
  }
*/
  if (!loraSerial.available()) return;

  byte marker = loraSerial.read();
  if (marker != 0xAA) return;  // wait for start marker

  if (!waitByte()) return;  // abort partial packet
  uint8_t count = loraSerial.read();
  
  if (count == 0 || count > 32) return;  // sanity check

  float received[32];
  for (uint8_t i = 0; i< count; i++){
    byte b[4];
    for (uint8_t j = 0; j< 4; j++){
      if (!waitByte()) return;  // abort partial packet
      b[j] = loraSerial.read();
    }
    memcpy(&received[i], b, 4);   // reassemble 4 bytes back into float
  }

  lcd.setCursor(10, 0);
  lcd.print(received[0]);
  lcd.setCursor(6, 1);
  lcd.print(received[1]);

  Serial.print("Depth: ");
  Serial.print(received[0]);
  Serial.println("cm");
  Serial.print("% :");
  Serial.println(received[1]);

  float pct = received[1];

  // Pump hysteresis: ON above 80, OFF below 10
  if (pct >= 80.0 && !pumpRunning) {
    pumpRunning = true;
  } else if (pct <= 10.0 && pumpRunning) {
    pumpRunning = false;
  }

  // Pump and LED output
  digitalWrite(ledPin, pumpRunning ? HIGH : LOW);

  // Buzzer: warn when critically low (< 10%)
  digitalWrite(buzzPin, (pct < 10.0) ? HIGH : LOW);

  // Optional: show idle state if nothing received for a while
  delay(100);
}