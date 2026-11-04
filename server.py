from flask import Flask, request
from datetime import datetime
import os
import requests
import base64
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

HACKCLUB_API_KEY = os.environ.get("HACKCLUB_API_KEY")
HACKCLUB_URL = "https://ai.hackclub.com/proxy/v1/chat/completions"

def check_screenshot(filepath, task_context):
    with open(filepath, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode('utf-8')

    payload = {
        "model": "google/gemini-3.5-flash",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": (
                        f"The kid is supposed to be doing this step: {task_context}. "
                        f"Look at this screenshot and tell me: are they on track, stuck, or done? "
                        f"Give a one-sentence answer a robot could say out loud to a kid."
                    )},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/png;base64,{image_b64}"
                    }}
                ]
            }
        ]
    }
    headers = {
        "Authorization": f"Bearer {HACKCLUB_API_KEY}",
        "Content-Type": "application/json"
    }

    resp = requests.post(HACKCLUB_URL, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

@app.route("/upload", methods=["POST"])
def upload():
    screenshot = request.files["screenshot"]
    task_id = request.form["task_id"]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{task_id}_{timestamp}.png"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    screenshot.save(filepath)

    print(f"Received Screenshot : {filename}")

    result = check_screenshot(filepath, "Open the Calculator app")
    print(f"Model says: {result}")

    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9999)