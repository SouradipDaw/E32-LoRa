#include<SoftwareSerial.h>

//Connect M0 and M1 to GND
const int rxPin = 10; // Connect to Module TXD
const int txPin = 11; // Connect to Module RXD (via 5V-to-3.3V voltage divider)

SoftwareSerial loraSerial(rxPin, txPin);

void sendFloatArray(float* arr, uint8_t count){
  loraSerial.write(0xAA);
  loraSerial.write(count);
  for(uint8_t i = 0; i< count; i++){
    byte b[4];
    memcpy(b, &arr[i], 4);
    loraSerial.write(b, 4);
  }
}

void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);
  loraSerial.begin(9600);
  Serial.println("Receiver ready");
}

void loop() {
  // put your main code here, to run repeatedly:
  float data[] = {100.5, 2.4, 5.8};
  uint8_t len = sizeof(data) / sizeof(data[0]);

  sendFloatArray(data, len);
  Serial.println("Packet Sent");

  delay(3000);
}
