import os
import json
import redis
from google import genai
from utils.colors import GREEN, RED, YELLOW, CYAN, MAGENTA, color

# ---------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------
REDIS_HOST = "localhost"
REDIS_PORT = 6379

MODEL_NAME = "models/gemini-2.5-flash"

API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    print("❌ ERROR: GOOGLE_API_KEY is not set!")
    exit(1)

# ---------------------------------------------------
# INIT GOOGLE CLIENT
# ---------------------------------------------------
client = genai.Client(api_key=API_KEY)

# ---------------------------------------------------
# REDIS CLIENT
# ---------------------------------------------------
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


# ---------------------------------------------------
# CLEAN GEMINI OUTPUT
# ---------------------------------------------------
def clean_json(text: str):
    """
    Removes ```json … ``` formatting and stray backticks.
    Ensures learner accepts Gemini responses correctly.
    """

    if not text:
        return text

    cleaned = text.strip()

    # Strip triple backticks
    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "")
        cleaned = cleaned.replace("```", "")
        cleaned = cleaned.strip()

    # Remove remaining backticks if any
    cleaned = cleaned.replace("```", "").replace("`", "").strip()
    return cleaned


# ---------------------------------------------------
# SEND PROMPT TO GEMINI
# ---------------------------------------------------
def ask_gemini(prompt):
    try:
        print(color(f"[LLM] Sending prompt to Gemini → {MODEL_NAME}", CYAN))

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )

        raw = response.text.strip()
        print(color(f"[LLM] Raw response → {raw}", MAGENTA))

        cleaned = clean_json(raw)

        # Try JSON parse
        try:
            action = json.loads(cleaned)
            return action
        except json.JSONDecodeError:
            print(color("⚠ Gemini returned invalid JSON → fallback to monitor", YELLOW))
            return None

    except Exception as e:
        print(color("❌ Gemini API Error: " + str(e), RED))
        return None


# ---------------------------------------------------
# BUILD PROMPT FOR GEMINI LLM
# ---------------------------------------------------
def build_prompt(context):
    return f"""
You are an autonomous cybersecurity decision-making AI.

Analyze this security alert:

{json.dumps(context, indent=2)}

Choose the BEST action.

Respond ONLY with a JSON dictionary. Valid actions:

1. {{"name": "block_ip", "params": {{"ip": "X.X.X.X"}}}}
2. {{"name": "alert_admin", "params": {{"message": "text"}}}}
3. {{"name": "monitor"}}

Output ONLY the JSON. No explanation, no markdown, no backticks.
"""


# ---------------------------------------------------
# MAIN EVENT LOOP
# ---------------------------------------------------
def main():
    print(color("🤖 LLM Learner (Gemini) is running... listening on decision_requests", GREEN))

    sub = redis_client.pubsub()
    sub.subscribe("decision_requests")

    for message in sub.listen():
        if message["type"] != "message":
            continue

        try:
            context = json.loads(message["data"])
        except:
            print(color("⚠ Invalid message received!", YELLOW))
            continue

        print(color(f"\n[LLM] Received context → {context}", CYAN))

        prompt = build_prompt(context)

        action = ask_gemini(prompt)

        if action is None:
            action = {"name": "monitor"}

        print(color(f"[LLM] Final decision → {action}", GREEN))

        redis_client.publish("actions", json.dumps(action))


if __name__ == "__main__":
    main()

