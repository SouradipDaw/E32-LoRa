#include <SoftwareSerial.h>

//Connect M0 and M1 to GND
const int rxPin = 10; // Connect to Module TXD
const int txPin = 11; // Connect to Module RXD (via 5V-to-3.3V voltage divider)

SoftwareSerial loraSerial(rxPin, txPin); 

const int auxPin = 13;  

void setup() {
  Serial.begin(9600);
  loraSerial.begin(9600); 

  pinMode(auxPin, INPUT);
//  pinMode(ledPin, OUTPUT);
//  digitalWrite(ledPin, LOW); 

  Serial.println("==========================================");
  Serial.println("     LORA KEYBOARD TRANSMITTER ACTIVE     ");
  Serial.println("==========================================");
  Serial.println("Type your message above and press ENTER:");
  Serial.println("------------------------------------------");
}

void loop() {
  if (Serial.available() > 0) {
    String userMessage = Serial.readStringUntil('\n');
    userMessage.trim(); 

    if (userMessage.length() > 0) {
      while (digitalRead(auxPin) == LOW) {
        delay(10);
      }

//      digitalWrite(ledPin, HIGH);
      loraSerial.println(userMessage);

      Serial.print("[Sent over Air]: ");
      Serial.println(userMessage);
      Serial.println(digitalRead(auxPin));

      delay(100);
      Serial.println(digitalRead(auxPin));

      while (digitalRead(auxPin) == LOW) {
        // Wait here while transmitting
      }
      
//      digitalWrite(ledPin, LOW);
    }
  }
}