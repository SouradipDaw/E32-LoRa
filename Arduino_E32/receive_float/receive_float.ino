#include<SoftwareSerial.h>

//Connect M0 and M1 to GND
const int rxPin = 10; // Connect to Module TXD
const int txPin = 11; // Connect to Module RXD (via 5V-to-3.3V voltage divider)

SoftwareSerial loraSerial(rxPin, txPin);

void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);
  loraSerial.begin(9600);
  Serial.println("Receiver ready");
}

void loop() {
  // put your main code here, to run repeatedly:
  if (!loraSerial.available()) return;

  byte b = loraSerial.read();
  if (b != 0xAA) return;  // wait for start marker

  while(!loraSerial.available());
  uint8_t count = loraSerial.read();
  
  if (count == 0 || count > 32) return;  // sanity check

  float received[32];
  for (uint8_t i = 0; i< count; i++){
    byte b[4];
    for (uint8_t j = 0; j< 4; j++){
      while(!loraSerial.available());
      b[j] = loraSerial.read();
    }
    memcpy(&received[i], b, 4);   // reassemble 4 bytes back into float
  }

  Serial.print("Received ");
  Serial.print(count);
  Serial.println(" integers:");
  for(uint8_t i=0; i< count; i++){
    Serial.print(" [");
    Serial.print(i);
    Serial.print("] = ");
    Serial.println(received[i]);
  }
}
