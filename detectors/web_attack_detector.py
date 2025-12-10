import json
import re
from datetime import datetime
import redis

redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)

SQLI_PATTERNS = [
    r"(\%27)|(\')|(\-\-)|(\%23)|(#)",
    r"(?i)(union(\s+)select)",
    r"(?i)(or(\s+)'1'='1')",
    r"(?i)(sleep\()",
]

LFI_PATTERNS = [
    r"(\.\./)+",
    r"(%2e%2e%2f)+",
    r"etc/passwd",
]

PATH_TRAVERSAL = [
    r"\.\./",
    r"%2e%2e%2f",
]

def matches(line, patterns):
    return any(re.search(p, line) for p in patterns)

def publish_alert(ip, attack_type, line):
    alert = {
        "id": f"web-{datetime.now().timestamp()}",
        "type": "web.attack.alert",
        "source": "detector",
        "stage": "web_attack",
        "attack_type": attack_type,
        "ip": ip,
        "payload": line,
        "severity": "high" if attack_type in ["SQLi", "LFI"] else "medium",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    redis_client.publish("alerts", json.dumps(alert))
    print(f"[WEB-DETECT] ALERT SENT → {attack_type} from {ip}")

def process_log(line):
    ip_match = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
    ip = ip_match.group(1) if ip_match else "unknown"

    if matches(line, SQLI_PATTERNS):
        publish_alert(ip, "SQLi", line)
        return

    if matches(line, LFI_PATTERNS):
        publish_alert(ip, "LFI", line)
        return

    if matches(line, PATH_TRAVERSAL):
        publish_alert(ip, "Path Traversal", line)
        return

def main():
    print("web-attack-detector listening on raw_logs ...")
    pubsub = redis_client.pubsub()
    pubsub.subscribe("raw_logs")

    for msg in pubsub.listen():
        if msg["type"] != "message":
            continue

        try:
            data = json.loads(msg["data"])
            line = data["line"]
        except:
            continue

        process_log(line)

if __name__ == "__main__":
    main()
