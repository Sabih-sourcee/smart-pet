from playsound3 import playsound
from faster_whisper import WhisperModel
import tempfile
from flask import Flask, request, send_from_directory
from datetime import datetime
import os
import requests
import base64
import json
from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI
tts_client = OpenAI(
    base_url="https://tts.ai/v1",
    api_key=os.environ.get("TTS_API_KEY")
)

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def load_session():
    path = os.path.join(UPLOAD_FOLDER, "session.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None

whisper_model = WhisperModel("small", device="cpu", compute_type="int8")

HACKCLUB_API_KEY = os.environ.get("HACKCLUB_API_KEY")
HACKCLUB_URL = "https://ai.hackclub.com/proxy/v1/chat/completions"

def check_screenshot(filepath, task_context):
    with open(filepath, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode('utf-8')

    payload = {
        "model": "anthropic/claude-sonnet-4.6",
        "max_tokens": 250,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": (
                        f"I am kid and i supposed to be doing this step: {task_context}. so break them all in 10 simple steps and help me do them all"
                        f"Look at this screenshot and tell me: am i on track, stuck, or done? "
                        f"Give a one-sentence answer to me so that i can understand what should be my next step after the current situation u saw in {task_context}."
                        f"If the user writes or speaks in Urdu, respond in Urdu. If in English, respond in English. and also dont use any kind of emoji or # in answer"
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

    resp = requests.post(HACKCLUB_URL, json=payload, headers=headers, timeout=60)
    if not resp.ok:
        print(f"Hack Club error: {resp.status_code} - {resp.text}")
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

def answer_question(question_text, task_context):
    payload = {
        "model": "anthropic/claude-sonnet-4.6",
        "max_tokens": 350,
        "messages": [
            {
                "role": "user",
                "content": (
                    f"I am a kid aged 11-15 is learning computers. I am working on: {task_context}. so break them all in 10 simple steps and help me do them all"
                    f"They asked: {question_text}. "
                    f"Answer in one or two simple sentences a friendly robot would say out loud."
                    f"If the user writes or speaks in Urdu, respond in Urdu. If in English, respond in English.and also dont use any kind of emoji or # in answer."
                )
            }
        ]
    }
    headers = {
        "Authorization": f"Bearer {HACKCLUB_API_KEY}",
        "Content-Type": "application/json"
    }
    resp = requests.post(HACKCLUB_URL, json=payload, headers=headers, timeout=60)
    if not resp.ok:
        print(f"Hack Club error: {resp.status_code} - {resp.text}")
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

def text_to_speech(text, output_path):
    import edge_tts
    is_urdu = any('\u0600' <= c <= '\u06FF' for c in text)
    voice = "ur-PK-AsadNeural" if is_urdu else "en-US-AriaNeural"
    communicate = edge_tts.Communicate(text, voice)
    communicate.save_sync(output_path)

def answer_question_with_screenshot(question, screenshot_path, history=[]):
    with open(screenshot_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()

    session = load_session()
    context = f"The kid is {session['name']} and wants to learn: {session['goal']}. " if session else ""

    messages = [
        {
            "role": "user",
            "content": f"You are Smart Pet, a friendly robot helping a Pakistani kid aged 11-15 learn computers. {context}You MUST explain everything yourself in simple words. NEVER tell the kid to search Google, use ChatGPT, or go to any website. NEVER redirect them anywhere. Always give the actual answer directly like you are a teacher sitting next to them. Keep responses to 2-3 simple sentences max. No emojis, no hashtags. If user writes in Urdu respond in Urdu, if English respond in English."
        }
    ]

for msg in history:
    if isinstance(msg["content"], str):
        messages.append({"role": msg["role"], "content": msg["content"]})
    else:
        messages.append({"role": msg["role"], "content": str(msg["content"])})
    
    messages.append({
        "role": "system",
        "content": [
            {"type": "text", "text": f"{question}. Important: continue helping me with what we were just dicussing only use the screenshot as extra context if relevant , do not change the topic based on what you see on screen."},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
        ]
    })

    payload = {
        "model": "anthropic/claude-sonnet-4.6",
        "max_tokens": 250,
        "messages": messages
    }
    headers = {
        "Authorization": f"Bearer {HACKCLUB_API_KEY}",
        "Content-Type": "application/json"
    }
    resp = requests.post(HACKCLUB_URL, json=payload, headers=headers, timeout=60)
    if not resp.ok:
        print(f"Hack Club error: {resp.status_code} - {resp.text}")
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

@app.route("/question_with_screenshot", methods=["POST"])
def question_with_screenshot():
    data = request.json
    question = data["question"]
    screenshot_b64 = data["screenshot"]
    
    # save screenshot temporarily
    img_data = base64.b64decode(screenshot_b64)
    tmp_path = os.path.join(UPLOAD_FOLDER, "chat_screenshot.png")
    with open(tmp_path, "wb") as f:
        f.write(img_data)

    history = data.get("history", [])
    answer = answer_question_with_screenshot(question, tmp_path, history)
    text_to_speech(answer, os.path.join(UPLOAD_FOLDER, "chat_response.mp3"))
    playsound(os.path.join(UPLOAD_FOLDER, "chat_response.mp3"))
    return answer, 200

@app.route("/upload", methods=["POST"])
def upload():
    screenshot = request.files["screenshot"]
    task_id = request.form["task_id"]
    task_context = request.form["task_context"]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{task_id}_{timestamp}.png"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    screenshot.save(filepath)
    print(f"Received Screenshot : {filename}")

    result = check_screenshot(filepath, task_context)
    print(f"Model says: {result}")

    audio_path = os.path.join(UPLOAD_FOLDER, f"{task_id}_response.mp3")
    text_to_speech(result, audio_path)
    print(f"Audio saved to: {audio_path}")
    playsound(audio_path)

    return "OK", 200

@app.route("/question", methods=["POST"])
def question():
    audio_file = request.files["audio"]
    task_context = request.form.get("task_context", "learning computers")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        audio_file.save(tmp.name)
        tmp_path = tmp.name

    segments, _ = whisper_model.transcribe(tmp_path, language="en")
    question_text = " ".join([s.text for s in segments]).strip()
    os.unlink(tmp_path)

    print(f"Kid asked: {question_text}")

    if not question_text:
        return "OK", 200

    answer = answer_question(question_text, task_context)
    print(f"Answer: {answer}")

    audio_path = os.path.join(UPLOAD_FOLDER, "question_response.mp3")
    text_to_speech(answer, audio_path)
    playsound(audio_path)

    return "OK", 200

@app.route("/onboard", methods=["POST"])
def onboard():
    data = request.json
    session = {"name": data["name"], "goal": data["goal"]}
    with open(os.path.join(UPLOAD_FOLDER, "session.json"), "w") as f:
        json.dump(session, f)
    return "OK", 200

@app.route("/speak", methods=["POST"])
def speak():
    text = request.json["text"]
    audio_path = os.path.join(UPLOAD_FOLDER, "speak.mp3")
    text_to_speech(text, audio_path)
    playsound(audio_path)
    return "OK", 200

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/session", methods=["GET"])
def session():
    path = os.path.join(UPLOAD_FOLDER, "session.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}, 200

@app.route("/screenshot", methods=["POST"])
def screenshot():
    import mss
    from PIL import Image
    import io
    with mss.MSS() as sct:
        monitor = sct.monitors[1]
        raw = sct.grab(monitor)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
    return {"screenshot": b64}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9999)