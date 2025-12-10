# state/state_manager.py

import json
import os
from utils.colors import GREEN, RED, YELLOW, color

STATE_FILE = "data/system_state.json"


class State:
    def __init__(self):
        self.state_file = STATE_FILE
        self.data = {
            "blocked_ips": [],
            "total_alerts": 0,
            "total_decisions": 0,
            "last_action": None
        }
        self.load()

    # ------------------------
    # Load state from JSON file
    # ------------------------
    def load(self):
        if not os.path.exists(self.state_file):
            self.save()
            return

        try:
            with open(self.state_file, "r") as f:
                self.data = json.load(f)
            print(color("[STATE] Loaded state file.", GREEN))

        except Exception as e:
            print(color(f"[STATE] Failed to load state: {e}", RED))

    # ------------------------
    # Save state to JSON file
    # ------------------------
    def save(self):
        try:
            with open(self.state_file, "w") as f:
                json.dump(self.data, f, indent=2)
            print(color("[STATE] Saved system state.", GREEN))

        except Exception as e:
            print(color(f"[STATE] Error saving state: {e}", RED))

    # ------------------------
    # Block IP
    # ------------------------
    def add_blocked_ip(self, ip):
        if ip not in self.data["blocked_ips"]:
            self.data["blocked_ips"].append(ip)
            self.data["last_action"] = f"Blocked {ip}"
            self.save()
            print(color(f"[STATE] Added blocked IP → {ip}", YELLOW))

    # ------------------------
    # Increase alert counter
    # ------------------------
    def increase_alert_count(self):
        self.data["total_alerts"] += 1
        self.save()

    # ------------------------
    # Increase decision counter
    # ------------------------
    def increase_decision_count(self):
        self.data["total_decisions"] += 1
        self.save()

    # ------------------------
    # Get full state
    # ------------------------
    def get(self):
        return self.data
