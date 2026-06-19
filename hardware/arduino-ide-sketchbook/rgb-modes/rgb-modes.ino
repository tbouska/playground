// ── Hardware ──────────────────────────────────────────────────────────────────

const int LED_PINS[]          = {0, 2, 15};  // R, G, B
const int PWM_FREQ_HZ         = 1000;
const int PWM_RESOLUTION_BITS = 12;
const int PWM_MAX             = (1 << PWM_RESOLUTION_BITS) - 1;

// ── Button ────────────────────────────────────────────────────────────────────

// One leg to BUTTON_PIN, other leg to GND. No resistor needed.
const int BUTTON_PIN  = 14;
const int DEBOUNCE_MS = 50;

// ── Colour helpers ────────────────────────────────────────────────────────────

const float GAMMA = 2.2f;

struct Rgb { uint16_t r, g, b; };

uint16_t applyGamma(float v) {
  return (uint16_t)(powf(constrain(v, 0.0f, 1.0f), GAMMA) * PWM_MAX + 0.5f);
}

Rgb makeRgb(float r, float g, float b) {
  return { applyGamma(r), applyGamma(g), applyGamma(b) };
}

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
  return makeRgb(r + m, g + m, b + m);
}

void writeRgb(const Rgb& c) {
  ledcWrite(LED_PINS[0], c.r);
  ledcWrite(LED_PINS[1], c.g);
  ledcWrite(LED_PINS[2], c.b);
}

// ── Modes ─────────────────────────────────────────────────────────────────────

void modeRainbow(unsigned long t) {
  writeRgb(hsvToRgb((float)(t % 12000) / 12000.0f * 360.0f, 1.0f, 1.0f));
}

void modeBreathe(unsigned long t) {
  float breath = (sinf(TWO_PI * t / 2000.0f) + 1.0f) * 0.5f;
  writeRgb(hsvToRgb((float)(t % 8000) / 8000.0f * 360.0f, 1.0f, breath));
}

void modePolice(unsigned long t) {
  switch ((t / 150) % 4) {
    case 0: writeRgb(makeRgb(1.0f, 0.0f, 0.0f)); break;
    case 1: writeRgb(makeRgb(0.0f, 0.0f, 0.0f)); break;
    case 2: writeRgb(makeRgb(0.0f, 0.0f, 1.0f)); break;
    case 3: writeRgb(makeRgb(0.0f, 0.0f, 0.0f)); break;
  }
}

void modeFire(unsigned long t) {
  float ms      = (float)t;
  float flicker = sinf(ms * 0.013f) * sinf(ms * 0.027f + 1.1f) * sinf(ms * 0.051f + 2.5f);
  float v       = constrain(0.75f + 0.25f * flicker, 0.2f, 1.0f);
  float hue     = 15.0f + 12.0f * sinf(ms * 0.005f);
  writeRgb(hsvToRgb(hue, 1.0f, v));
}

void modeDisco(unsigned long t) {
  uint32_t h = ((uint32_t)(t / 120)) * 2654435761UL;
  writeRgb(hsvToRgb((float)(h % 360), 1.0f, 1.0f));
}

void modeHeartbeat(unsigned long t) {
  unsigned long phase = t % 1000;
  float brightness    = 0.0f;
  if      (phase <  80)  brightness = phase / 80.0f;
  else if (phase < 200)  brightness = (200.0f - phase) / 120.0f;
  else if (phase < 280)  brightness = (phase - 200.0f) / 80.0f;
  else if (phase < 400)  brightness = (400.0f - phase) / 120.0f;
  writeRgb(hsvToRgb(0.0f, 1.0f, constrain(brightness, 0.0f, 1.0f)));
}

// ── Mode sequencer ────────────────────────────────────────────────────────────

struct ModeEntry { void (*update)(unsigned long t); };

const ModeEntry MODES[] = {
  { modeRainbow   },
  { modeBreathe   },
  { modePolice    },
  { modeFire      },
  { modeDisco     },
  { modeHeartbeat },
};

const int MODE_COUNT = sizeof(MODES) / sizeof(MODES[0]);

int           modeIndex   = 0;
unsigned long modeStartMs = 0;

void advanceMode() {
  modeIndex   = (modeIndex + 1) % MODE_COUNT;
  modeStartMs = millis();

  // Brief white flash confirms the press
  writeRgb(makeRgb(1.0f, 1.0f, 1.0f));
  delay(80);
}

// ── Button handler (canonical Arduino debounce) ────────────────────────────────

int           stableButtonState = HIGH;
int           lastButtonReading = HIGH;
unsigned long lastDebounceTime  = 0;

void handleButton() {
  int           reading = digitalRead(BUTTON_PIN);
  unsigned long now     = millis();

  if (reading != lastButtonReading) {
    lastDebounceTime  = now;
    lastButtonReading = reading;
  }

  if ((now - lastDebounceTime) > DEBOUNCE_MS && reading != stableButtonState) {
    stableButtonState = reading;
    if (stableButtonState == LOW) {  // falling edge = confirmed press
      advanceMode();
    }
  }
}

// ── Arduino entry points ──────────────────────────────────────────────────────

void setup() {
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  for (int i = 0; i < 3; i++) {
    ledcAttach(LED_PINS[i], PWM_FREQ_HZ, PWM_RESOLUTION_BITS);
  }
  modeStartMs = millis();
}

void loop() {
  handleButton();

  unsigned long modeT = millis() - modeStartMs;
  MODES[modeIndex].update(modeT);
}