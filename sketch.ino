#include <ESP32Servo.h>

Servo myServo;

const int servoPin = 5;
const int buttonPin = 4;

int currentAngle = 0;
int targetAngle = 0;

int lastButtonState = HIGH;
int currentButtonState = HIGH;

unsigned long lastDebounceTime = 0;
const unsigned long debounceDelay = 50;

unsigned long lastServoUpdate = 0;
const unsigned long servoInterval = 20;

void setup() {
  Serial.begin(115200);

  pinMode(buttonPin, INPUT_PULLUP);

  myServo.attach(servoPin);
  myServo.write(0);

  Serial.println("Smart Pet Controller V3 Ready!");
  Serial.println("Servo Position: 0 degrees");
}

void loop() {

  // BUTTON DETECTION AND DEBOUNCING
  int reading = digitalRead(buttonPin);

  if (reading != lastButtonState) {
    lastDebounceTime = millis();
  }

  if ((millis() - lastDebounceTime) > debounceDelay) {

    if (reading != currentButtonState) {

      currentButtonState = reading;

      if (currentButtonState == LOW) {

        if (targetAngle == 0) {
          targetAngle = 90;
          Serial.println("Target Position: 90 degrees");
        }
        else {
          targetAngle = 0;
          Serial.println("Target Position: 0 degrees");
        }
      }
    }
  }

  lastButtonState = reading;

  // NON-BLOCKING SERVO MOVEMENT
  if (millis() - lastServoUpdate >= servoInterval) {

    lastServoUpdate = millis();

    if (currentAngle < targetAngle) {
      currentAngle++;
      myServo.write(currentAngle);
    }

    else if (currentAngle > targetAngle) {
      currentAngle--;
      myServo.write(currentAngle);
    }
  }
}
