"""
Smart Pet - Screenshot Capture Client
Takes a screenshot every N seconds and uploads it to the server.

Install deps first:
    pip install mss requests pillow

Usage:
    python screenshot_capture.py --server http://your-server:5000/upload --task-id abc123
"""

import argparse
import io
import time
from datetime import datetime, timezone

import requests
import mss
from PIL import Image


def capture_screenshot() -> bytes:
    """Capture the primary monitor and return PNG bytes."""
    with mss.MSS() as sct:
        monitor = sct.monitors[1]  # 0 = all monitors combined, 1 = primary
        raw = sct.grab(monitor)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()


def upload_screenshot(server_url: str, task_id: str, task_context: str, image_bytes: bytes) -> bool:
    try:
        files = {"screenshot": ("capture.png", image_bytes, "image/png")}
        data = {
            "task_id": task_id,
            "task_context": task_context,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }
        resp = requests.post(server_url, files=files, data=data, timeout=15)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"[WARN] Upload failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Smart Pet screenshot capture loop")
    parser.add_argument("--server", required=True, help="Upload endpoint URL")
    parser.add_argument("--task-id", required=True, help="ID of the current task session")
    parser.add_argument("--task", required=True, help="What the kid is supposed to be doing right now")
    parser.add_argument("--interval", type=int, default=60, help="Seconds between captures")
    args = parser.parse_args()

    print(f"Smart Pet capture started. Interval: {args.interval}s. Task: {args.task_id}")
    print("Press Ctrl+C to stop.\n")

    capture_count = 0

    try:
        while True:
            start = time.time()

            image_bytes = capture_screenshot()
            ok = upload_screenshot(args.server, args.task_id, args.task, image_bytes)

            capture_count += 1
            status = "sent" if ok else "FAILED"
            print(f"[{capture_count}] {datetime.now().strftime('%H:%M:%S')} - capture {status}")

            elapsed = time.time() - start
            sleep_for = max(0, args.interval - elapsed)
            time.sleep(sleep_for)

    except KeyboardInterrupt:
        print(f"\nStopped. Total captures: {capture_count}")


if __name__ == "__main__":
    main()
