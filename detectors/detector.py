import time, json, uuid, random, os
import redis
import numpy as np
from sklearn.ensemble import IsolationForest
from joblib import dump, load

# -----------------------------
# Redis Connection
# -----------------------------
REDIS_URL = "redis://localhost:6379/0"
r = redis.Redis.from_url(REDIS_URL)

# Model storage path
MODEL_PATH = os.path.join(os.path.dirname(__file__), '../data/models/detector_if.joblib')

# -----------------------------
# Feature Generator (Simulated)
# -----------------------------
def gen_features(is_attack=False):
    base_rate = random.uniform(1, 10)
    if is_attack:
        rate = base_rate * random.uniform(10, 30)
        distinct_uris = random.randint(50, 200)
    else:
        rate = base_rate * random.uniform(0.5, 1.5)
        distinct_uris = random.randint(1, 10)
    return {"rate": rate, "distinct_uris": distinct_uris}

# -----------------------------
# Train Model (Only First Time)
# -----------------------------
def train_model():
    if os.path.exists(MODEL_PATH):
        print("➡ Loading existing model...")
        return load(MODEL_PATH)

    print("⚙ Training IsolationForest model for anomaly detection...")
    X = []
    for _ in range(1000):
        f = gen_features(is_attack=False)
        X.append([f["rate"], f["distinct_uris"]])

    model = IsolationForest(contamination=0.01, random_state=42)
    model.fit(np.array(X))

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    dump(model, MODEL_PATH)
    print("✅ Model saved:", MODEL_PATH)

    return model

# -----------------------------
# Main Loop
# -----------------------------
def main_loop():
    model = train_model()
    iteration = 0

    while True:
        iteration += 1

        # 5% chance it's an attack
        is_attack = (random.random() < 0.05)
        features = gen_features(is_attack=is_attack)

        x = np.array([[features["rate"], features["distinct_uris"]]])
        score = model.decision_function(x)[0]
        is_anomaly = model.predict(x)[0] == -1
        confidence = float(abs(score))

        if is_anomaly:
            alert = {
                "id": f"alert-{uuid.uuid4()}",
                "type": "detection.alert",
                "source": "detector-1",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "payload": {
                    "attacker_ip": f"10.0.0.{random.randint(2,254)}",
                    "confidence": confidence,
                    "tags": ["anomaly"],
                    "features": features
                }
            }

            r.publish("alerts", json.dumps(alert))
            print(f"🚨 ALERT SENT → {alert['id']}  features={features}")

        else:
            if iteration % 50 == 0:
                print("Normal events flowing...")

        time.sleep(0.5)


if __name__ == "__main__":
    main_loop()
