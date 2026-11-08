import requests
import base64
import mss
import io
from PIL import Image

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

print("Smart Pet: Hi! I can see your screen. Ask me anything!")

while True:
    question = input("You: ")
    if question.lower() == "exit":
        break
    screenshot = base64.b64encode(capture()).decode()
    answer = ask(question, screenshot)
    print(f"Smart Pet: {answer}")