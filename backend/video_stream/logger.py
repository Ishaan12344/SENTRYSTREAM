import csv
import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = os.path.join(BASE_DIR, "output", "logs")

os.makedirs(LOG_DIR, exist_ok=True)

CSV_FILE = os.path.join(LOG_DIR, "events.csv")
JSON_FILE = os.path.join(LOG_DIR, "violations_log.json")

# Create CSV header
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "violations"])


def log_event(violations):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, ",".join(violations)])


def log_violation_json(report):

    if not os.path.exists(JSON_FILE):
        with open(JSON_FILE, "w") as f:
            json.dump([], f)

    try:
        with open(JSON_FILE, "r+") as f:
            data = json.load(f)
            data.append(report)
            f.seek(0)
            json.dump(data, f, indent=2)
    except Exception as e:
        print("Error writing JSON log:", e)