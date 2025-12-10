import json
import redis
import re
import time
from datetime import datetime, timezone

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

print("\n🚀 SSH DEBUG DETECTOR STARTED — Listening on raw_logs ...\n")

# REGEX must match EXACT log lines
SSH_FAIL_PATTERN = re.compile(
    r".*Failed password.*from (\d{1,3}(?:\.\d{1,3}){3}).*"
)

# Track failed attempts per IP
FAILED = {}
WINDOW = 10       # seconds
THRESHOLD = 5     # >= 5 attempts → alert

def debug_print(prefix, msg):
    print(f"[DEBUG][SSH][{prefix}] {msg}")

def publish_alert(ip, attempts):
    alert = {
        "type": "bruteforce.alert",
        "source": "detector",
        "stage": "ssh_bruteforce",
        "severity": "medium",
        "ip": ip,
        "attempts": attempts,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    r.publish("alerts", json.dumps(alert))
    print("\n🔥🔥 SSH ALERT SENT! 🔥🔥")
    print(alert)
    print("----------------------------------------------------\n")

def handle_log(line):
    debug_print("LOG_RECEIVED", line)

    match = SSH_FAIL_PATTERN.match(line)
    if not match:
        debug_print("NO_MATCH", "Regex did NOT match this log.")
        return

    ip = match.group(1)
    now = time.time()

    debug_print("MATCH", f"Matched IP → {ip}")

    FAILED.setdefault(ip, [])
    FAILED[ip].append(now)

    # keep only last 10 seconds
    FAILED[ip] = [t for t in FAILED[ip] if now - t <= WINDOW]

    attempts = len(FAILED[ip])
    debug_print("ATTEMPTS", f"{ip} → {attempts} attempts")

    if attempts >= THRESHOLD:
        publish_alert(ip, attempts)
        FAILED[ip] = []


def main():
    p = r.pubsub()
    p.subscribe("raw_logs")

    for msg in p.listen():
        if msg["type"] != "message":
            continue
        handle_log(msg["data"])


if __name__ == "__main__":
    main()
