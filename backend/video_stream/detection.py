from ultralytics import YOLO
import cv2
import datetime
import os
import json
import time
import threading
import requests

from logger import log_event, log_violation_json
from config import ALLOWED_CLASSES, VIOLATION_CLASSES

# 🔥 CHANGE THIS
BACKEND_URL = "http://192.168.X.X:8000/report"

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
USE_WEBCAM = False
IP_CAMERA_URL = "http://192.168.29.100:8080/video"

CONFIDENCE_THRESHOLD = 0.45
VIOLATION_COOLDOWN_SEC = 7
BLOCK_TIME_SEC = 300
SKIP_FRAMES = 2

# ─────────────────────────────────────────────
# STOP CONTROL
# ─────────────────────────────────────────────
exit_flag = False


def send_to_backend(image_path, report):
    try:
        with open(image_path, "rb") as img:
            files = {"image": img}
            data = {"data": json.dumps(report)}

            res = requests.post(BACKEND_URL, files=files, data=data)

            print("📡 Sent:", res.status_code)

    except Exception as e:
        print("❌ Backend error:", e)


def listen_for_exit():
    global exit_flag
    input("\n🔴 Press ENTER anytime to STOP...\n")
    exit_flag = True


threading.Thread(target=listen_for_exit, daemon=True).start()

# ─────────────────────────────────────────────
# PATH SETUP
# ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OUTPUT_IMAGES = os.path.join(BASE_DIR, "output", "images")
OUTPUT_VIOLATIONS = os.path.join(BASE_DIR, "output", "violations")
OUTPUT_LOGS = os.path.join(BASE_DIR, "output", "logs")

for folder in [OUTPUT_IMAGES, OUTPUT_VIOLATIONS, OUTPUT_LOGS]:
    os.makedirs(folder, exist_ok=True)

# ─────────────────────────────────────────────
# MODEL
# ─────────────────────────────────────────────
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "best.pt")

print(f"Loading model: {MODEL_PATH}")
model = YOLO(MODEL_PATH)

print("Model loaded.\n")


# ─────────────────────────────────────────────
# CAMERA
# ─────────────────────────────────────────────
def open_camera(source):
    cap = cv2.VideoCapture(source)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


source = 0 if USE_WEBCAM else IP_CAMERA_URL
cap = open_camera(source)

if not cap.isOpened():
    print("❌ Cannot open camera")
    exit()

print("🚀 SentryStream running...")

cv2.namedWindow("SentryStream", cv2.WINDOW_NORMAL)
cv2.resizeWindow("SentryStream", 900, 600)

# ─────────────────────────────────────────────
# GLOBAL STATE
# ─────────────────────────────────────────────
last_saved_time = None
person_violation_memory = {}

# ─────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────
while True:

    if exit_flag:
        print("🛑 Stopping...")
        break

    # Skip frames
    for _ in range(SKIP_FRAMES):
        cap.grab()

    ret, frame = cap.retrieve()

    if not ret:
        print("⚠️ Reconnecting...")
        cap.release()
        time.sleep(2)
        cap = open_camera(source)
        continue

    # YOLO Tracking
    results = model.track(frame, conf=CONFIDENCE_THRESHOLD, persist=True, verbose=False)

    annotated = frame.copy()
    violations = []
    detections = []

    now = datetime.datetime.now()
    ts_str = now.strftime("%Y-%m-%d %H:%M:%S")

    # ─────────────────────────────────────────
    # DETECTIONS (SAFE)
    # ─────────────────────────────────────────
    if results and len(results) > 0 and results[0].boxes is not None:

        for box in results[0].boxes:

            cls_id = int(box.cls[0])
            label = model.names[cls_id]
            conf = float(box.conf[0])

            if label not in ALLOWED_CLASSES:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0])

            track_id = int(box.id[0]) if box.id is not None else None
            is_violation = label in VIOLATION_CLASSES

            detections.append(
                {
                    "label": label,
                    "confidence": round(conf, 3),
                    "bbox": [x1, y1, x2, y2],
                    "track_id": track_id,
                    "violation": is_violation,
                }
            )

            # 🔥 Block duplicate violations
            if is_violation and track_id is not None:
                key = (track_id, label)
                last_time = person_violation_memory.get(key)

                if (
                    last_time is None
                    or (now - last_time).total_seconds() >= BLOCK_TIME_SEC
                ):
                    person_violation_memory[key] = now
                    violations.append(f"{label} (ID {track_id})")

            # Draw
            color = (0, 0, 255) if is_violation else (0, 255, 0)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            text = f"{label} ID:{track_id} {conf:.2f}"
            cv2.putText(
                annotated,
                text,
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2,
            )

    else:
        print("⚠️ No detections in this frame")

    # ─────────────────────────────────────────
    # SAVE + SEND
    # ─────────────────────────────────────────
    if violations:

        if (
            last_saved_time is None
            or (now - last_saved_time).total_seconds() >= VIOLATION_COOLDOWN_SEC
        ):

            last_saved_time = now
            file_ts = now.strftime("%Y%m%d_%H%M%S")

            img_path = os.path.join(OUTPUT_IMAGES, f"violation_{file_ts}.jpg")
            cv2.imwrite(img_path, annotated)

            report = {
                "timestamp": ts_str,
                "violations": list(set(violations)),
                "detections": detections,
                "image": img_path,
                "camera": str(source),
            }

            # 🔥 SEND TO BACKEND
            send_to_backend(img_path, report)

            # Save JSON locally
            json_path = os.path.join(OUTPUT_VIOLATIONS, f"violation_{file_ts}.json")

            try:
                with open(json_path, "w") as f:
                    json.dump(report, f, indent=2)
            except Exception as e:
                print("JSON error:", e)

            log_event(violations)
            log_violation_json(report)

            print(f"\n🚨 VIOLATION: {list(set(violations))}")
            print(f"Saved: {img_path}")

    # DISPLAY
    cv2.imshow("SentryStream", annotated)

    if cv2.waitKey(1) == 27:
        print("🛑 ESC pressed. Exiting...")
        break

# CLEANUP
cap.release()
cv2.destroyAllWindows()
print("Stopped.")
