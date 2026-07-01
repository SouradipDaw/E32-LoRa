#include "LoRa_E32.h"

// adjust pins to your wiring
LoRa_E32 e32ttl(10, 11, 5, 6, 7);  // RX, TX, AUX, M0, M1

void setup() {
  Serial.begin(9600);
  e32ttl.begin();

  // Configure this module
  ResponseStructContainer c = e32ttl.getConfiguration();
  Configuration config = *(Configuration*) c.data;

  config.ADDH = 0x00;
  config.ADDL = 0x02;                                        // This module's address
  config.CHAN = 0x04;                                        // Same channel as transmitter
  config.OPTION.fixedTransmission = FT_FIXED_TRANSMISSION;
  config.SPED.airDataRate = AIR_DATA_RATE_010_24;
  config.SPED.uartBaudRate = UART_BPS_9600;
  config.OPTION.transmissionPower = POWER_20;

  e32ttl.setConfiguration(config, WRITE_CFG_PWR_DWN_SAVE);
  c.close();

  Serial.println("Receiver ready");
}

void loop() {
  if (e32ttl.available() > 1) {
    ResponseStructContainer rsc = e32ttl.receiveMessage(16);  // length of "Hello from 0001!"
    String message = (char*) rsc.data;
    Serial.println("Received: " + message);
    rsc.close();
  }
}