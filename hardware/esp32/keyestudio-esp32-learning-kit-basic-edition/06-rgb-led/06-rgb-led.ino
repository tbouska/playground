// Pins for R, G, B
int ledPins[] = {0, 2, 15};

void setup() {
  for (int i = 0; i < 3; i++) {
    ledcAttach(ledPins[i], 1000, 8);  // pin, 1 kHz, 8-bit resolution
  }
}

void setColor(int r, int g, int b) {
  ledcWrite(ledPins[0], r);
  ledcWrite(ledPins[1], g);
  ledcWrite(ledPins[2], b);
}

void loop() {
  setColor(255, 0,   0);   delay(1000);  // red
  setColor(0,   255, 0);   delay(1000);  // green
  setColor(0,   0,   255); delay(1000);  // blue
  setColor(255, 255, 0);   delay(1000);  // yellow
  setColor(0,   255, 255); delay(1000);  // cyan
  setColor(255, 0,   255); delay(1000);  // magenta
  setColor(255, 255, 255); delay(1000);  // white
}