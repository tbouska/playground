#define PIN_LED_RED     0
#define PIN_LED_YELLOW  2
#define PIN_LED_GREEN  15

#define BLINK_DURATION_MIN_MS 150
#define BLINK_DURATION_MAX_MS 500

// Sequence order: red → yellow → green
const uint8_t LED_SEQUENCE[] = { PIN_LED_RED, PIN_LED_YELLOW, PIN_LED_GREEN };
const uint8_t LED_COUNT = sizeof(LED_SEQUENCE) / sizeof(LED_SEQUENCE[0]);

void setup() {
  // Seed with floating analog pin for true randomness
  randomSeed(analogRead(A0));

  for (uint8_t i = 0; i < LED_COUNT; i++) {
    pinMode(LED_SEQUENCE[i], OUTPUT);
  }
}

void loop() {
  for (uint8_t i = 0; i < LED_COUNT; i++) {
    uint16_t duration = random(BLINK_DURATION_MIN_MS, BLINK_DURATION_MAX_MS + 1);
    digitalWrite(LED_SEQUENCE[i], HIGH);
    delay(duration);
    digitalWrite(LED_SEQUENCE[i], LOW);
  }
}