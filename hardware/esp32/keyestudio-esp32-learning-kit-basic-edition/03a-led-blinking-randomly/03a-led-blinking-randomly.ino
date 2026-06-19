//*******************************************************************************
/*
 * Filename    : External LED flashing
 * Description : Make an led blinking.
 * Author      : http//www.keyestudio.com
*/
#define PIN_LED   15   //define the led pin

// the setup function runs once when you press reset or power the board
void setup() {
  // initialize digital pin LED as an output.
  pinMode(PIN_LED, OUTPUT);
  randomSeed(analogRead(A0));
}

// the loop function runs over and over again forever
void loop() {
  digitalWrite(PIN_LED, HIGH);   // turn the LED on (HIGH is the voltage level)
  delay(random(200, 1500));
  digitalWrite(PIN_LED, LOW);    // turn the LED off by making the voltage LOW
  delay(random(200, 1500));
}
//*******************************************************************************
