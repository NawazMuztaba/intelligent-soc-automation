import redis
import json
import time
import re
from datetime import datetime

# -----------------------------
# CONFIG
# -----------------------------
REDIS_HOST = "localhost"
REDIS_PORT = 6379

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# -----------------------------
# REGEX PATTERN (FIXED)
# Matches logs like:
# Dec 09 12:31 kali sshd[999]: Failed password for test from 10.0.0.55 port 22
# -----------------------------
AUTH_FAIL_REGEX = re.compile(
    r".*Failed password for (invalid user )?(\w+) from ([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)"
)

# -----------------------------
# STATE (sliding window)
# -----------------------------
attempts_by_ip = {}
WINDOW_SECONDS = 10
THRESHOLD = 5


def publish_alert(ip, stage, severity, attempts):
    """Send alert event to orchestrator."""
    alert = {
        "id": f"alert-{int(time.time()*1000)}",
        "type": "bruteforce.alert",
        "source": "detector",
        "severity": severity,
        "ip": ip,
        "stage": stage,
        "attempts": attempts,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    redis_client.publish("alerts", json.dumps(alert))
    print(f"[BRUTE][{stage}] ALERT PUBLISHED -> {ip} severity={severity} attempts={attempts}")


def process_auth_log(line):
    """Extract brute-force patterns from auth logs."""
    match = AUTH_FAIL_REGEX.search(line)
    if not match:
        return

    _, username, ip = match.groups()
    now = time.time()

    if ip not in attempts_by_ip:
        attempts_by_ip[ip] = []

    # Add attempt timestamp
    attempts_by_ip[ip].append(now)

    # Remove old attempts outside time window
    attempts_by_ip[ip] = [
        t for t in attempts_by_ip[ip] if now - t <= WINDOW_SECONDS
    ]

    attempts = len(attempts_by_ip[ip])

    # Determine stage and severity
    if attempts >= THRESHOLD:
        stage = "password_spray"
        severity = "medium"
        publish_alert(ip, stage, severity, attempts)


def main():
    print("bruteforce-detector listening on raw_logs ...")

    pubsub = redis_client.pubsub()
    pubsub.subscribe("raw_logs")

    for message in pubsub.listen():
        if message["type"] != "message":
            continue

        try:
            data = json.loads(message["data"])
        except:
            continue

        if "line" not in data:
            continue

        line = data["line"]
        process_auth_log(line)


if __name__ == "__main__":
    main()
