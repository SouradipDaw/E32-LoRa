#include<LiquidCrystal.h>
#include<SoftwareSerial.h>

LiquidCrystal lcd(8, 9, 4, 5, 6, 7);

const int trigpin = 2;
const int echopin = 3;

//Connect M0 and M1 to GND
const int rxPin = 10; // Connect to Module TXD
const int txPin = 11; // Connect to Module RXD (via 5V-to-3.3V voltage divider)

SoftwareSerial loraSerial(rxPin, txPin); 

const int auxPin = 13; 

void ultrasonic(float* out) {
  digitalWrite(trigpin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigpin, HIGH);
  delayMicroseconds(10);          // fixed
  digitalWrite(trigpin, LOW);

  long duration = pulseIn(echopin, HIGH, 26000);
  float distance = 0.0343 * duration / 2.0;
  out[0] = distance;
  out[1] = distance / 2.0;
}


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
  pinMode(trigpin, OUTPUT);
  pinMode(echopin, INPUT);
  pinMode(12, OUTPUT);
  lcd.begin(16, 2);
  lcd.setCursor(3, 0);
  lcd.print("Depth: ");
  lcd.setCursor(3, 1);
  lcd.print("%: ");
  loraSerial.begin(9600); 
  pinMode(auxPin, INPUT);
}

void loop() {
  float data[2];
  ultrasonic(data);

  uint8_t len = sizeof(data) / sizeof(data[0]);

  lcd.setCursor(10, 0);
  lcd.print(data[0]);
  lcd.setCursor(6, 1);
  lcd.print(data[1]);

  Serial.print("Depth: ");
  Serial.print(data[0]);
  Serial.println(" cm");
  Serial.print("%: ");
  Serial.println(data[1]);

  while (digitalRead(auxPin) == LOW);  // wait until module idle
  sendFloatArray(data, len);
  while (digitalRead(auxPin) == LOW);  // wait until TX complete
  Serial.println("Packet Sent");

  delay(3000);
}
