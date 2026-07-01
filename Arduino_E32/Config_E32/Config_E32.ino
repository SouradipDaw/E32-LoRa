#include <SoftwareSerial.h>

//Connect M0 and M1 to 3.3 V

const int rxPin = 10; // Connect to Module TXD
const int txPin = 11; // Connect to Module RXD (via 5V-to-3.3V voltage divider)

SoftwareSerial moduleSerial(rxPin, txPin);

void setup() {
  Serial.begin(9600);
  moduleSerial.begin(9600);

  // M0=HIGH, M1=HIGH for config mode
  delay(500);

  Serial.println("Writing config...");

  // Address 0x0000, channel 0x06, 9600 baud, 2.4k air, 20dBm
  byte config[] = {0xC0, 0x00, 0x00, 0x1A, 0x06, 0x44};
  moduleSerial.write(config, 6);

  delay(500);

  // Verify by reading back
  byte verify[] = {0xC1, 0xC1, 0xC1};
  moduleSerial.write(verify, 3);

  delay(500);

  if (moduleSerial.available()) {
    Serial.print("Verified config: ");
    while (moduleSerial.available()) {
      byte b = moduleSerial.read();
      if (b < 0x10) Serial.print("0");
      Serial.print(b, HEX);
      Serial.print(" ");
      delay(10);
    }
    Serial.println();
  }
}

void loop() {}