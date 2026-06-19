// Pins wired to R, G, B legs of the LED
const int           LED_PINS[]          = {0, 2, 15};
const int           PWM_FREQ_HZ         = 1000;
const int           PWM_RESOLUTION_BITS = 12;             // 0–4095
const int           PWM_MAX             = (1 << PWM_RESOLUTION_BITS) - 1;
const unsigned long CYCLE_MS           = 12000;          // 12-second cycle
const float         GAMMA               = 2.2f;           // perceptual correction

struct Rgb {
  uint16_t r, g, b;
};

// Maps a linear 0.0–1.0 channel value to a gamma-corrected PWM duty cycle.
uint16_t applyGamma(float linear) {
  float clamped = constrain(linear, 0.0f, 1.0f);
  return (uint16_t)(powf(clamped, GAMMA) * PWM_MAX + 0.5f);
}

// Converts HSV to gamma-corrected PWM RGB values.
// h: 0–360 degrees, s and v: 0.0–1.0
Rgb hsvToRgb(float h, float s, float v) {
  float c = v * s;
  float x = c * (1.0f - fabsf(fmodf(h / 60.0f, 2.0f) - 1.0f));
  float m = v - c;

  float r, g, b;
  if      (h <  60.0f) { r = c; g = x; b = 0.0f; }
  else if (h < 120.0f) { r = x; g = c; b = 0.0f; }
  else if (h < 180.0f) { r = 0.0f; g = c; b = x; }
  else if (h < 240.0f) { r = 0.0f; g = x; b = c; }
  else if (h < 300.0f) { r = x; g = 0.0f; b = c; }
  else                 { r = c; g = 0.0f; b = x; }

  return { applyGamma(r + m), applyGamma(g + m), applyGamma(b + m) };
}

void writeRgb(const Rgb& color) {
  ledcWrite(LED_PINS[0], color.r);
  ledcWrite(LED_PINS[1], color.g);
  ledcWrite(LED_PINS[2], color.b);
}

void setup() {
  for (int i = 0; i < 3; i++) {
    ledcAttach(LED_PINS[i], PWM_FREQ_HZ, PWM_RESOLUTION_BITS);
  }
}

void loop() {
  float hue   = (float)(millis() % CYCLE_MS) / CYCLE_MS * 360.0f;
  Rgb   color = hsvToRgb(hue, 1.0f, 1.0f);
  writeRgb(color);
}