#include <OneWire.h>
#include <SoftwareSerial.h>

SoftwareSerial moduleSerial(10,11);

// Data wire is connected to digital pin 2
const int ONE_WIRE_BUS = 2;

// Instantiate the OneWire object
OneWire ds(ONE_WIRE_BUS);


void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);
  moduleSerial.begin(9600);
  delay(100);
  Serial.println("TX ready, sending...");
}

void loop() {
  // put your main code here, to run repeatedly:
  byte data[12];
  byte addr[8];

  // Look for a 1-Wire device on the bus
  if ( !ds.search(addr)) {
    ds.reset_search();
    delay(250);
    return;
  }

  // Verify the CRC of the address to ensure it's a valid device
  if (OneWire::crc8(addr, 7) != addr[7]) {
      Serial.println("CRC is not valid!");
      return;
  }
  
  // Verify that the device is indeed a DS18B20 (Family code 0x28)
  if (addr[0] != 0x28) {
      Serial.println("Device is not a DS18B20 family device.");
      return;
  }

  // --- Step 1 & 2: Tell the sensor to start measuring temperature ---
  ds.reset();
  ds.select(addr);
  ds.write(0x44, 1);        // 0x44 = Convert T command (1 keeps parasite power on if used)
  
  delay(750);               // Wait 750ms for 12-bit temperature conversion to complete
  
  // --- Step 3: Read the raw data from the scratchpad ---
  byte present = ds.reset();
  ds.select(addr);    
  ds.write(0xBE);           // 0xBE = Read Scratchpad command

  // Read the 9 bytes of the scratchpad
  for (int i = 0; i < 9; i++) {
    data[i] = ds.read();
  }

  // --- Step 4: Mathematical byte conversion ---
  // Combine Byte 0 (LSB) and Byte 1 (MSB) into a single 16-bit signed integer
  int16_t raw = (data[1] << 8) | data[0];
  
  // The default resolution is 12-bit. In 12-bit mode, each bit represents 0.0625°C.
  // We divide by 16.0 (or multiply by 0.0625) to convert the raw reading to Celsius.
  float celsius = (float)raw / 16.0;
  float fahrenheit = celsius * 1.8 + 32.0;
  
  // Print results
  moduleSerial.print("Temperature: ");
  moduleSerial.print(celsius);
  moduleSerial.print("°C  |  ");
  moduleSerial.print(fahrenheit);
  moduleSerial.println("°F");

  Serial.print("Temperature: ");
  Serial.print(celsius);
  Serial.print("°C  |  ");
  Serial.print(fahrenheit);
  Serial.println("°F");

  delay(1000); // Wait before the next reading
}
