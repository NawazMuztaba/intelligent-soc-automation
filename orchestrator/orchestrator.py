# orchestrator/orchestrator.py

import json
import redis
from utils.colors import GREEN, RED, YELLOW, CYAN, MAGENTA, color
from state.state_manager import State


# -------------------------------
# REDIS CONFIG
# -------------------------------

REDIS_HOST = "localhost"
REDIS_PORT = 6379

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
state = State()


# -------------------------------
# PROCESS ALERT → BUILD CONTEXT
# -------------------------------

def process_alert(raw):
    """
    Converts detector alert → LLM context packet
    """

    try:
        alert = json.loads(raw)
    except:
        print(color("[ORCH] Invalid alert received!", RED))
        return None

    print(color(f"\n🧠 Orchestrator received alert → {alert['id']}", CYAN))

    state.increase_alert_count()

    context = {
        "id": alert["id"],
        "type": alert.get("type", "unknown"),
        "source": alert.get("source", "detector"),
        "severity": alert.get("severity", "low"),
        "ip": alert.get("ip"),
        "stage": alert.get("stage", ""),
        "attempts": alert.get("attempts", 0),
    }

    print(color(f"[ORCH] Built context → {context}", MAGENTA))
    return context


# -------------------------------
# SEND TO LLM LEARNER
# -------------------------------

def send_to_learner(context):
    redis_client.publish("decision_requests", json.dumps(context))
    print(color(f"📤 Decision request sent → {context}", YELLOW))


# -------------------------------
# RECEIVE ACTIONS FROM LLM → STATE + RESPONDER
# -------------------------------
# Replace your existing handle_action(...) with this exact function
# ------------------------------
# FINAL FIXED handle_action()
# ------------------------------

import json
import hashlib
import time

DEDUP_TTL = 30  # seconds


def action_fingerprint(action_obj):
    j = json.dumps(action_obj, sort_keys=True, separators=(',', ':'))
    return hashlib.sha1(j.encode()).hexdigest()


def handle_action(action_raw):
    """Process an action safely without loops or duplicates."""
    try:
        action = json.loads(action_raw)
    except:
        print(color("[ORCH] Invalid JSON received", RED))
        return

    # ---- dedupe start ----
    fp = action_fingerprint(action)
    key = f"orch:dedupe:{fp}"

    try:
        if not redis_client.setnx(key, int(time.time())):
            print(color(f"[ORCH] Ignored duplicate action fp={fp}", YELLOW))
            return
        redis_client.expire(key, DEDUP_TTL)
    except Exception as e:
        print(color(f"[ORCH] Redis dedupe failed: {e}", YELLOW))
    # ---- dedupe end ----

    print(color(f"🤖 Final Action Received → {action}", GREEN))

    # ----- update state safely -----
    try:
        state.increase_decision_count()
    except:
        pass

    # ----- action handler -----
    try:
        name = action.get("name")

        if name == "block_ip":
            ip = action["params"]["ip"]
            state.add_blocked_ip(ip)
            print(color(f"[ORCH] Added blocked IP → {ip}", CYAN))

        elif name == "alert_admin":
            msg = action["params"]["message"]
            state.save_admin_alert(msg)
            print(color(f"[ORCH] Admin alert saved", CYAN))

        elif name == "monitor":
            pass

        else:
            print(color(f"[ORCH] Unknown action {name}", YELLOW))

    except Exception as e:
        print(color(f"[ORCH] Action handler error: {e}", RED))

    # IMPORTANT: DO NOT RE-PUBLISH THE ACTION
    # redis_client.publish("actions", json.dumps(action))   ← MUST REMAIN COMMENTED
    return

# -------------------------------
# MAIN LOOP
# -------------------------------

def main():
    print(color("🧠 Orchestrator running... listening on alerts + actions", GREEN))

    sub = redis_client.pubsub()
    sub.subscribe("alerts", "actions")

    for msg in sub.listen():
        if msg["type"] != "message":
            continue

        channel = msg["channel"]
        data = msg["data"]

        if channel == "alerts":
            context = process_alert(data)
            if context:
                send_to_learner(context)

        elif channel == "actions":
            handle_action(data)


if __name__ == "__main__":
    main()
