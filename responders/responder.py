import redis
import json
import hashlib
import time
import os
import sys

# -----------------------
# Redis connection
# -----------------------
redis_client = redis.Redis(host="localhost", port=6379, db=0)
sub = redis_client.pubsub()
sub.subscribe("actions")

print("🛡 Responder is live... listening on: actions")

# -----------------------
# Deduplication settings
# -----------------------
DEDUP_TTL = 30  # seconds


def action_fingerprint(action_obj):
    """
    Creates a stable fingerprint of an action using SHA1 hashing.
    Ensures duplicate actions are detected even if Redis replays them.
    """
    j = json.dumps(action_obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(j.encode("utf-8")).hexdigest()


# -----------------------
# MAIN LISTEN LOOP
# -----------------------
for message in sub.listen():

    # skip non-message events
    if message["type"] != "message":
        continue

    raw = message["data"]

    # parse safely
    try:
        action = json.loads(raw)
    except Exception:
        print("[RESPONDER] Invalid JSON received")
        continue

    # ---------------------------
    # DEDUPLICATION STARTS HERE
    # ---------------------------
    fp = action_fingerprint(action)
    dedupe_key = f"responder:dedupe:{fp}"

    # Only allow action if Redis key does NOT exist
    if not redis_client.setnx(dedupe_key, int(time.time())):
        print(f"[RESPONDER] Ignoring duplicate action (fp={fp})")
        continue

    # Expire dedupe lock after TTL
    redis_client.expire(dedupe_key, DEDUP_TTL)
    # ---------------------------
    # DEDUPLICATION ENDS HERE
    # ---------------------------

    print(f"[RESPONDER] Received → {action}")

    # ---------------------------
    # ACTION HANDLERS
    # ---------------------------

    name = action.get("name")
    params = action.get("params", {})

    # ---- block_ip ----
    if name == "block_ip":
        ip = params.get("ip")

        if ip:
            print(f"🛡 BLOCKING IP: {ip}")
            result = os.system(f"sudo iptables -A INPUT -s {ip} -j DROP")
            print("🛡 IPTABLES RESULT:", result)
        else:
            print("[RESPONDER] Missing IP in block_ip action")

    # ---- alert_admin ----
    elif name == "alert_admin":
        msg = params.get("message", "")
        print(f"📢 ADMIN ALERT → {msg}")

    # ---- unknown action ----
    else:
        print(f"[RESPONDER] Unknown action → {name}")
