#include <SoftwareSerial.h>

// Increase buffer size before instantiation
#define _SS_MAX_RX_BUFF 256

//Connect M0 and M1 to GND
const int rxPin = 10; // Connect to Module TXD
const int txPin = 11; // Connect to Module RXD (via 5V-to-3.3V voltage divider)

SoftwareSerial loraSerial(rxPin, txPin); 

const int auxPin = 13;  
// const int ledPin = 13; 

void setup() {
  Serial.begin(9600);
  loraSerial.begin(9600); 

  pinMode(auxPin, INPUT);
//  pinMode(ledPin, OUTPUT);
//  digitalWrite(ledPin, LOW); 

  Serial.println("==========================================");
  Serial.println("     LORA DEDICATED RECEIVER ACTIVE       ");
  Serial.println("     Waiting for wireless data...         ");
  Serial.println("==========================================");
}

void loop() {
  if (loraSerial.available() > 0) {
//    digitalWrite(ledPin, HIGH);

    String receivedPayload = loraSerial.readStringUntil('\n');
    receivedPayload.trim(); 

    Serial.println("\n[!] NEW WIRELESS PACKET RECEIVED:");
    Serial.print("Message: ");
    Serial.println(receivedPayload);
    Serial.println("------------------------------------------");

    delay(200);
//    digitalWrite(ledPin, LOW);
  }

}


/*void loop() {
  // Raw byte dump — bypasses any parsing issues
  if (loraSerial.available()) {
    byte b = loraSerial.read();
    Serial.print("0x");
    Serial.print(b, HEX);
    Serial.println(" ");
  }
}*/

/*void loop() {
  if (loraSerial.available()) {
    while (loraSerial.available()) {
      Serial.write(loraSerial.read());  // use write() not print()
    }
  }
}*/

/*void loop() {
  if (loraSerial.available() > 0) {
    String receivedPayload = "";
    
    unsigned long lastByte = millis();
    while (millis() - lastByte < 100) {
      if (loraSerial.available()) {
        char c = loraSerial.read();
        if (c != '\r' && c != '\n') {
          receivedPayload += c;
        }
        lastByte = millis();
      }
    }

    if (receivedPayload.length() > 0) {
      Serial.println("\n[!] NEW WIRELESS PACKET RECEIVED:");
      Serial.print("Message: ");
      Serial.println(receivedPayload);
      Serial.println("------------------------------------------");
    }
  }
}*/