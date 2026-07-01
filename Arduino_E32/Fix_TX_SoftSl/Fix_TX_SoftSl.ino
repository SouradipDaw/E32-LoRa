#include <SoftwareSerial.h>

#define M0_PIN 6 // Connected via 5V-to-3.3V voltage divider
#define M1_PIN 7 // Connected via 5V-to-3.3V voltage divider
#define AUX_PIN 13 

const int rxPin = 10; // Connect to Module TXD
const int txPin = 11; // Connect to Module RXD (via 5V-to-3.3V voltage divider)

SoftwareSerial e32Serial(rxPin, txPin);

// Wait for AUX pin to go HIGH (module ready)
void waitAUX() {
  while (digitalRead(AUX_PIN) == LOW);
  delay(10);
}

// Enter Sleep Mode (M0=1, M1=1) for configuration
void sleepMode() {
  digitalWrite(M0_PIN, HIGH);
  digitalWrite(M1_PIN, HIGH);
  delay(100);
  waitAUX();
}

// Enter Normal Mode (M0=0, M1=0) for TX/RX
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
   * ADDL = 0x01  → address 0x0001
   * SPED = 0x1A  → 9600 baud (bits 5-3: 011), 2.4k air rate (bits 2-0: 010), 8N1 (bits 7-6: 00)
   *               binary: 00 011 010 = 0x1A
   * CHAN = 0x04  → 862 + 4 = 866 MHz
   * OPTION = 0xC4 → bit7=1 (fixed transmission), bit6=1 (push-pull IO), bits5-3=000, bits1-0=00 (30dBm)
   *               binary: 1100 0100 = 0xC4
   */
  byte config[] = {0xC0, 0x00, 0x01, 0x1A, 0x04, 0xC4};
  e32Serial.write(config, 6);
  delay(100);

  // Read back confirmation
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
  Serial.println("Transmitter ready");
}

void loop() {
  waitAUX();

  /*
   * Fixed transmission format: ADDH + ADDL + CHAN + data
   * Send to address 0x0002 on channel 0x04
   */
  String msg = "Hello from 0001!";
  byte header[] = {0x00, 0x02, 0x04};  // target ADDH, ADDL, CHAN
  e32Serial.write(header, 3);
  e32Serial.print(msg);

  Serial.println("Sent: " + msg);
  Serial.println(digitalRead(AUX_PIN));
  delay(1000);
  Serial.println(digitalRead(AUX_PIN));
  delay(2000);
}