import requests
import base64
import mss
import io
import os
from PIL import Image
import time

SERVER = "http://localhost:9999"

def capture():
    with mss.MSS() as sct:
        monitor = sct.monitors[1]
        raw = sct.grab(monitor)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

def ask(question, screenshot_b64):
    resp = requests.post(f"{SERVER}/question_with_screenshot", json={
        "question": question,
        "screenshot": screenshot_b64
    })
    return resp.text

def speak(text):
    requests.post(f"{SERVER}/speak", json={"text": text})
    print(f"Smart Pet: {text}")

def onboard():
    speak("Hi! I am Smart Pet. What is your name?")
    name = input("You: ").strip()
    speak(f"Nice to meet you {name}! What do you want to learn today?")
    goal = input("You: ").strip()
    requests.post(f"{SERVER}/onboard", json={"name": name, "goal": goal})
    speak(f"Great! Lets get started {name}!")

if not os.path.exists("uploads/session.json"):
    onboard()

print("Smart Pet is ready. Ask me anything!")

while True:
    question = input("You: ")
    if question.lower() == "exit":
        break
    screenshot = base64.b64encode(capture()).decode()
    answer = ask(question, screenshot)
    time.sleep(4)
    print(f"Smart Pet: {answer}")