from playsound3 import playsound
from faster_whisper import WhisperModel
import tempfile
from flask import Flask, request
from datetime import datetime
import os
import requests
import base64
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
whisper_model = WhisperModel("small", device="cpu", compute_type="int8")

HACKCLUB_API_KEY = os.environ.get("HACKCLUB_API_KEY")
HACKCLUB_URL = "https://ai.hackclub.com/proxy/v1/chat/completions"

def check_screenshot(filepath, task_context):
    with open(filepath, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode('utf-8')

    payload = {
        "model": "anthropic/claude-sonnet-4.6",
        "max_tokens": 200,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": (
                        f"I am kid and i supposed to be doing this step: {task_context}. "
                        f"Look at this screenshot and tell me: am i on track, stuck, or done? "
                        f"Give a one-sentence answer to me so that i can understand what should be my next step after the current situation u saw in {task_context}."
                        f"If the user writes or speaks in Urdu, respond in Urdu. If in English, respond in English."
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
        "max_tokens": 150,
        "messages": [
            {
                "role": "user",
                "content": (
                    f"A kid aged 11-15 is learning computers. They are working on: {task_context}. "
                    f"They asked: {question_text}. "
                    f"Answer in one or two simple sentences a friendly robot would say out loud."
                    f"If the user writes or speaks in Urdu, respond in Urdu. If in English, respond in English."
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

def answer_question_with_screenshot(question, screenshot_path):
    with open(screenshot_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()
    
    payload = {
        "model": "anthropic/claude-sonnet-4.6",
        "max_tokens": 150,
        "messages": [{
            "role": "user",
            "content": [
        {"type": "text", "text": f"A kid asked: {question}. Look at their screen and answer in 1-2 simple friendly sentences. If the user writes or speaks in Urdu, respond in Urdu. If in English, respond in English."},
    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
]
        }]
    }
    headers = {
        "Authorization": f"Bearer {HACKCLUB_API_KEY}",
        "Content-Type": "application/json"
    }
    resp = requests.post(HACKCLUB_URL, json=payload, headers=headers, timeout=60)
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
    
    answer = answer_question_with_screenshot(question, tmp_path)
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9999)