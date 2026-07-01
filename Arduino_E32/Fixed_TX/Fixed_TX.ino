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
  config.ADDL = 0x01;                                        // This module's address
  config.CHAN = 0x04;                                        // Channel
  config.OPTION.fixedTransmission = FT_FIXED_TRANSMISSION;
  config.SPED.airDataRate = AIR_DATA_RATE_010_24;
  config.SPED.uartBaudRate = UART_BPS_9600;
  config.OPTION.transmissionPower = POWER_20;

  e32ttl.setConfiguration(config, WRITE_CFG_PWR_DWN_SAVE);
  c.close();

  Serial.println("Transmitter ready");
}

void loop() {
  String message = "Hello from 0001!";
  ResponseStatus rs = e32ttl.sendMessage(message);

  if (rs.code == 1) {
    Serial.println("Message sent successfully");
  } else {
    Serial.println("Send failed: " + String(rs.getResponseDescription()));
  }

  delay(3000);
}