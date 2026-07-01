#include <SoftwareSerial.h>

//Connect M0 and M1 to 3.3 V
// Using healthy digital pins to bypass the fried hardware UART pins (0 and 1)
const int rxPin = 10; // Connect to Module TXD
const int txPin = 11; // Connect to Module RXD (via 5V-to-3.3V voltage divider)

SoftwareSerial moduleSerial(rxPin, txPin);

void setup() {
  // Initialize communication with your PC Serial Monitor
  Serial.begin(9600);
  while (!Serial) {
    ; // Wait for the serial port to connect
  }
  
  // Initialize communication with the wireless module
  moduleSerial.begin(9600); 

  Serial.println("--- Module Recovery & Diagnostic Tool ---");
  Serial.println("Hardware: Using Pins 10 (RX) and 11 (TX).");
  Serial.println("Ensure M0 and M1 are securely tied HIGH (VCC).");
  Serial.println("----------------------------------------");
  Serial.println("Type '1' to read Parameters (Fixes FF FF FF loop)");	// FF FF FF loop appears if C0 C0 C0 command is sent
  Serial.println("Type '2' to request Firmware Info (C3 C3 C3)");
  Serial.println("----------------------------------------\n");
}

void loop() {
  // 1. Listen for commands from the PC Serial Monitor
  if (Serial.available() > 0) {
    char choice = Serial.read();
    
    if (choice == '1') {
      Serial.println("[Action] Flushing buffer and querying parameters...");
      
      // FIX: Aggressively read and discard any residual floating/FF bytes 
      // in the serial line before we send our official request.
      while (moduleSerial.available() > 0) {
        moduleSerial.read(); 
      }
      delay(50); // Small pause to let lines stabilize

      // Send Parameter Query
      byte cmd[] = {0xC1, 0xC1, 0xC1};
      moduleSerial.write(cmd, 3);
    } 
    else if (choice == '2') {
      Serial.println("[Action] Querying Firmware Info...");
      
      // Send Firmware Query
      byte cmd[] = {0xC3, 0xC3, 0xC3};
      moduleSerial.write(cmd, 3);
    }
  }

  // 2. Listen for and format the module's response
  if (moduleSerial.available() > 0) {
    Serial.print("[Response Hex]: ");
    
    // Read the incoming bytes
    while (moduleSerial.available() > 0) {
      byte resp = moduleSerial.read();
      
      // Format single-digit hex values nicely (e.g., 'F' becomes '0F')
      if (resp < 0x10) Serial.print("0"); 
      Serial.print(resp, HEX);
      Serial.print(" ");
      
      delay(10); // Tiny delay to allow the hardware serial buffer to catch up
    }
    Serial.println("\n");
  }
}