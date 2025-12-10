# ~/agentic-orchestrator/dashboard/api.py
from flask import Flask, jsonify, request
from flask_cors import CORS
import redis
import json
from datetime import datetime, timezone
import threading
import time

app = Flask(__name__)
CORS(app)

# Redis client (adjust host/port if needed)
r = redis.Redis(host="localhost", port=6379, decode_responses=True)

# In-memory store (last N alerts)
MAX_ALERTS = 1000
ALERTS = []

# Simple stats (rolling)
STATS = {
    "total": 0,
    "by_type": {},
    "by_severity": {}
}

# optional: whether API should enqueue "actions" to redis (set to False while testing)
ENQUEUE_ACTIONS = False


def add_alert(alert):
    # normalize minimal fields
    alert.setdefault("received_at", datetime.now(timezone.utc).isoformat())
    ALERTS.append(alert)
    if len(ALERTS) > MAX_ALERTS:
        ALERTS.pop(0)

    # update stats
    STATS["total"] += 1
    t = alert.get("type", "unknown")
    s = alert.get("severity", "unknown")
    STATS["by_type"][t] = STATS["by_type"].get(t, 0) + 1
    STATS["by_severity"][s] = STATS["by_severity"].get(s, 0) + 1


@app.route("/api/alerts", methods=["GET"])
def get_alerts():
    # supports ?limit=100 and ?since=<ISO timestamp>
    limit = int(request.args.get("limit", 200))
    since = request.args.get("since")
    data = ALERTS[-limit:]
    if since:
        try:
            data = [a for a in data if a.get("received_at", "") > since]
        except:
            pass
    return jsonify(list(reversed(data)))


@app.route("/api/stats", methods=["GET"])
def get_stats():
    # return basic stats and counts for charts
    recent_count = len(ALERTS)
    return jsonify({
        "total_received": STATS["total"],
        "current_buffer": recent_count,
        "by_type": STATS["by_type"],
        "by_severity": STATS["by_severity"]
    })


@app.route("/api/action/block", methods=["POST"])
def block_ip():
    """
    Enqueue a block_ip action to the 'actions' channel.
    Body: {"ip":"1.2.3.4", "reason":"optional text"}
    This will NOT run iptables itself; it just places an action into Redis for orchestrator/ responder.
    """
    body = request.get_json(force=True, silent=True) or {}
    ip = body.get("ip")
    reason = body.get("reason", "blocked via dashboard")
    if not ip:
        return jsonify({"ok": False, "error": "missing ip"}), 400

    action = {
        "name": "block_ip",
        "params": {"ip": ip, "reason": reason},
        "meta": {"source": "dashboard", "ts": datetime.now(timezone.utc).isoformat()}
    }

    # Optionally publish but default disabled while you test to avoid loops
    if ENQUEUE_ACTIONS:
        try:
            r.publish("actions", json.dumps(action))
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    # Return back the action so UI can show success locally
    return jsonify({"ok": True, "action": action})


def listen_for_alerts():
    pubsub = r.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe("alerts")
    print("📡 dashboard listener: subscribed to 'alerts' channel")
    for msg in pubsub.listen():
        if msg["type"] != "message":
            continue
        try:
            data = msg["data"]
            # message could be either a JSON string or already a Python object depending on producer
            if isinstance(data, str):
                alert = json.loads(data)
            else:
                alert = data  # hope it's already a dict
            # ensure timestamps
            alert.setdefault("received_at", datetime.now(timezone.utc).isoformat())
            add_alert(alert)
            print("📥 dashboard received alert:", alert.get("id") or alert.get("type"))
        except Exception as e:
            print("⚠ dashboard error parsing alert:", e)


if __name__ == "__main__":
    t = threading.Thread(target=listen_for_alerts, daemon=True)
    t.start()
    # Run flask app
    app.run(host="0.0.0.0", port=5000, debug=True)
