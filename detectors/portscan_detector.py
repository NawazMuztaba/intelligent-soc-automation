import json
import redis
import time
import re
from datetime import datetime, timezone

redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)

print("portscan-detector (GROUPED MODE) listening on raw_logs ...")

SCAN_PATTERN = re.compile(r"from (\d+\.\d+\.\d+\.\d+) on port (\d+)")
WINDOW_SECONDS = 3

# Temporary storage
port_buffer = {}
last_alert_time = {}

def publish_grouped_alert(ip, ports):
    alert = {
        "type": "portscan.group.alert",
        "ip": ip,
        "ports": sorted(list(ports)),
        "total_ports": len(ports),
        "severity": "high",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    redis_client.publish("alerts", json.dumps(alert))
    print("\n[PORTSCAN-GROUP] ALERT SENT →")
    print(json.dumps(alert, indent=2))

def process_log(line):
    match = SCAN_PATTERN.search(line)
    if not match:
        return

    ip, port = match.groups()
    port = int(port)

    now = time.time()

    if ip not in port_buffer:
        port_buffer[ip] = []

    # Add port
    port_buffer[ip].append((now, port))

    # Filter only last WINDOW_SECONDS seconds
    port_buffer[ip] = [(t, p) for t, p in port_buffer[ip] if now - t <= WINDOW_SECONDS]

    ports_only = {p for _, p in port_buffer[ip]}

    # Fire alert when ≥ 10 unique ports scanned
    if len(ports_only) >= 10:
        last_time = last_alert_time.get(ip, 0)
        if now - last_time >= WINDOW_SECONDS:
            publish_grouped_alert(ip, ports_only)
            last_alert_time[ip] = now

def main():
    pubsub = redis_client.pubsub()
    pubsub.subscribe("raw_logs")

    for msg in pubsub.listen():
        if msg["type"] != "message":
            continue
        process_log(msg["data"])

if __name__ == "__main__":
    main()
