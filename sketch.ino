#include <ESP32Servo.h>
Servo smartServo;

// Pin configuration
const int SERVO_PIN = 18;
const int BUTTON_PIN = 4;

// Servo positions
const int OPEN_POS = 90;
const int CLOSE_POS = 0;
const int CENTER_POS = 45;

// Movement variables
int currentPosition = 45;
int targetPosition = 45;

unsigned long previousMoveTime = 0;
const int moveInterval = 15;

// Button debounce variables
int lastButtonReading = HIGH;
int stableButtonState = HIGH;
unsigned long lastDebounceTime = 0;
const unsigned long debounceDelay = 50;

// Button toggle state — kept in sync with every serial command too
bool buttonOpen = false;

// Serial command
String command = "";

void setup() {
  Serial.begin(115200);

  pinMode(BUTTON_PIN, INPUT_PULLUP);

  smartServo.attach(SERVO_PIN);
  smartServo.write(currentPosition);

  Serial.println("Smart Pet V4 Started!");
  Serial.println("Commands: OPEN, CLOSE, CENTER, STATUS");
}

void loop() {

  // 1. Read computer commands
  if (Serial.available() > 0) {
    command = Serial.readStringUntil('\n');
    command.trim();
    command.toUpperCase();

    if (command == "OPEN") {
      targetPosition = OPEN_POS;
      buttonOpen = true;
      Serial.println("Moving to OPEN position");

    } else if (command == "CLOSE") {
      targetPosition = CLOSE_POS;
      buttonOpen = false;
      Serial.println("Moving to CLOSE position");

    } else if (command == "CENTER") {
      targetPosition = CENTER_POS;
      // Convention: CENTER counts as "closed" for toggle purposes,
      // so the next button press moves to OPEN, not back to CENTER.
      buttonOpen = false;
      Serial.println("Moving to CENTER position");

    } else if (command == "STATUS") {
      Serial.print("Current: ");
      Serial.print(currentPosition);
      Serial.print(" | Target: ");
      Serial.print(targetPosition);
      Serial.print(" | ButtonState: ");
      Serial.println(buttonOpen ? "OPEN" : "CLOSE");

    } else {
      Serial.println("Invalid command");
    }
  }

  // 2. Read physical button
  int reading = digitalRead(BUTTON_PIN);

  if (reading != lastButtonReading) {
    lastDebounceTime = millis();
  }

  if ((millis() - lastDebounceTime) > debounceDelay) {

    if (reading != stableButtonState) {
      stableButtonState = reading;

      if (stableButtonState == LOW) {
        buttonOpen = !buttonOpen;

        targetPosition = buttonOpen ? OPEN_POS : CLOSE_POS;

        Serial.println("Button command received");
      }
    }
  }

  lastButtonReading = reading;

  // 3. Smooth non-blocking servo movement
  if (currentPosition != targetPosition) {

    if (millis() - previousMoveTime >= moveInterval) {

      previousMoveTime = millis();

      if (currentPosition < targetPosition) {
        currentPosition++;
      } else {
        currentPosition--;
      }

      smartServo.write(currentPosition);
    }
  }
}