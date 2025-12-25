//**********************************************************************
/*
 * Filename    : Breathing Led
 * Description : Make led light fade in and out, just like breathing.
 * Author      : http//www.keyestudio.com
 * Updated     : Adapted for ESP32 Arduino Core v3.0+ by tbouska
*/

#define PIN_LED   15    // define the led pin
#define FRQ       1000  // define the pwm frequency
#define PWM_BIT   8     // define the pwm precision

void setup() {
  // v3.0 Change: ledcAttach replaces ledcSetup and ledcAttachPin
  // Syntax: ledcAttach(pin, frequency, resolution)
  ledcAttach(PIN_LED, FRQ, PWM_BIT);
}

void loop() {
  // Make light fade in
  for (int i = 0; i < 255; i++) {
    // v3.0 Change: ledcWrite now takes the PIN, not the channel
    ledcWrite(PIN_LED, i);
    delay(10);
  }
  
  // Make light fade out
  for (int i = 255; i > -1; i--) {
    ledcWrite(PIN_LED, i);
    delay(10);
  }
}
//*************************************************************************************
