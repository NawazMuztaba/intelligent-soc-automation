#!/usr/bin/env python3
import redis, json, uuid, time
from datetime import datetime

REDIS_URL = "redis://localhost:6379/0"
r = redis.Redis.from_url(REDIS_URL)

# -----------------------------------------------------
# Simple rule + RL-based decision engine
# -----------------------------------------------------
def decide_action(ctx):
    """
    Decide action based on context.
    Handles:
      - brute-force attacks
      - ML anomalies
      - future detectors
    """

    alert_type = ctx.get("type")

    # ============================================
    # 1. Bruteforce attacks (our new detector)
    # ============================================
    if alert_type == "bruteforce":
        stage = ctx.get("stage")
        severity = ctx.get("severity")
        ip = ctx.get("ip")

        # HIGH severity → block IP
        if severity == "high":
            return {
                "name": "block_ip",
                "params": {"ip": ip}
            }

        # MEDIUM severity → alert admin
        if severity == "medium":
            return {
                "name": "alert_admin",
                "params": {"message": f"Suspicious activity from {ip}"}
            }

        # low severity
        return {
            "name": "monitor",
            "params": {}
        }

    # ============================================
    # 2. ML anomaly detector
    # ============================================
    if alert_type == "anomaly":
        features = ctx.get("features", {})
        rate = features.get("rate", 0)

        if rate > 100:
            return {
                "name": "rate_limit",
                "params": {"value": rate}
            }
        else:
            return {
                "name": "monitor",
                "params": {}
            }

    # ============================================
    # 3. Unknown alert type
    # ============================================
    return {
        "name": "monitor",
        "params": {}
    }


# -----------------------------------------------------
# MAIN LOOP
# -----------------------------------------------------
def main():
    print("🤖 Learner running... listening on decision_requests")

    pubsub = r.pubsub()
    pubsub.subscribe("decision_requests")

    for msg in pubsub.listen():
        if msg["type"] != "message":
            continue

        try:
            data = json.loads(msg["data"].decode())
        except:
            print("Bad JSON received")
            continue

        ctx = data.get("context", {})
        action = decide_action(ctx)

        print(f"🤖 Learner: action → {action}")

        # Publish action to "commands" for responder
        r.publish("commands", json.dumps(action))


if __name__ == "__main__":
    main()
