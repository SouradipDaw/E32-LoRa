#include <SoftwareSerial.h>

#define M0_PIN 6
#define M1_PIN 7
#define AUX_PIN 13

const int rxPin = 10; // Connect to Module TXD
const int txPin = 11; // Connect to Module RXD (via 5V-to-3.3V voltage divider)

SoftwareSerial e32Serial(rxPin, txPin);

void waitAUX() {
  while (digitalRead(AUX_PIN) == LOW);
  delay(10);
}

void sleepMode() {
  digitalWrite(M0_PIN, HIGH);
  digitalWrite(M1_PIN, HIGH);
  delay(100);
  waitAUX();
}

void normalMode() {
  digitalWrite(M0_PIN, LOW);
  digitalWrite(M1_PIN, LOW);
  delay(100);
  waitAUX();
}

void configureModule() {
  sleepMode();

  /*
   * Command: C0 ADDH ADDL SPED CHAN OPTION
   *
   * ADDH = 0x00
   * ADDL = 0x02  → address 0x0002
   * SPED = 0x1A  → same as transmitter (must match air data rate)
   * CHAN = 0x04  → same channel as transmitter
   * OPTION = 0xC4 → fixed transmission, push-pull, 30dBm
   */
  byte config[] = {0xC0, 0x00, 0x02, 0x1A, 0x04, 0xC4};
  e32Serial.write(config, 6);
  delay(100);

  while (e32Serial.available()) {
    Serial.print(e32Serial.read(), HEX);
    Serial.print(" ");
  }
  Serial.println();

  normalMode();
}

void setup() {
  Serial.begin(9600);
  e32Serial.begin(9600);

  pinMode(M0_PIN, OUTPUT);
  pinMode(M1_PIN, OUTPUT);
  pinMode(AUX_PIN, INPUT);

  configureModule();
  Serial.println("Receiver ready, waiting...");
}

void loop() {
  if (e32Serial.available()) {
    String received = "";
    while (e32Serial.available()) {
      received += (char)e32Serial.read();
      delay(2); // small gap to allow full message to arrive
    }
    Serial.println("Received: " + received);
  }
}