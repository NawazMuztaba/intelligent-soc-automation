🔥 Intelligent SOC Automation System
Real-Time Threat Detection | Log Monitoring | Attack Visualization Dashboard

This project is a complete Security Operations Center (SOC) automation system that detects cyberattacks in real-time, processes logs, generates alerts, and visualizes them on a modern dashboard UI.

It includes:

✔ Log Adapter
✔ Multiple Attack Detectors
✔ Real-Time Alert Streaming
✔ Modern React Dashboard
✔ Grouped Portscan Detection
✔ SSH Bruteforce Detection
✔ SQL Injection Detection
✔ Redis-Backed Event Pipeline
✔ Extendable Machine Learning Framework

🚀 Features
🔹 1. Real-Time Log Adapter

Reads logs from multiple files simultaneously:

SSH authentication logs

Portscan logs

Web attack logs (SQLi, XSS patterns)

Publishes logs into Redis channels for processing.

🔹 2. Attack Detectors (Python)

Each detector listens on Redis → processes logs → sends alerts.

🟦 SSH Bruteforce Detector

Tracks repeated failed login attempts

Automatically groups attempts

Sends alert after threshold reached

🟧 Portscan Detector (GROUPED MODE)

Detects multi-port scanning

Groups ports scanned within a time window

Sends a single clean alert

Looks clean on dashboard

🟩 Web Attack Detector

Detects simple SQL injection & suspicious patterns.

🔹 3. Beautiful React Security Dashboard

Displays alerts in real time with:

Severity badges (High / Medium / Low)

Modern dark UI

Icons for different alert types

Grouped Portscan alerts

Smooth layout and readable formatting

🧠 Architecture Overview
Logs → Log Adapter → Redis → Detectors → Redis(alerts) → Flask API → React Dashboard


Technologies used:

Python

Redis

Flask

React.js

Tailwind/Dark Theme UI

Shell scripts for responders

🛠️ Project Structure
agentic-orchestrator/
│
├── adapters/
│   └── log_adapter.py
│
├── detectors/
│   ├── ssh_bruteforce_detector.py
│   ├── portscan_detector.py
│   ├── web_attack_detector.py
│
├── dashboard/
│   ├── api.py         (Flask backend)
│   └── ui/            (React frontend)
│
├── responders/
│   └── playbooks/
│       └── block_ip.sh
│
├── utils/
├── data/
└── orchestrator/

⚙️ How to Run (Local Setup)
1️⃣ Start Redis
sudo systemctl start redis-server

2️⃣ Run Backend API
cd dashboard
source ../venv/bin/activate
python api.py

3️⃣ Start Log Adapter
cd ~/agentic-orchestrator
python adapters/log_adapter.py \
  -w ~/logs/ssh_test.log:auth \
  -w ~/logs/portscan_test.log:port \
  -w ~/logs/web_test.log:web

4️⃣ Run Detectors
python detectors/ssh_bruteforce_detector.py
python detectors/portscan_detector.py
python detectors/web_attack_detector.py

5️⃣ Start Dashboard UI
cd dashboard/ui
npm install
npm start

🧪 Testing the Detection System
✔ SSH Bruteforce Simulation

Run 5 times:

echo "Dec 10 10:31 sshd[111]: Failed password for root from 22.22.22.22 port 22" >> ~/logs/ssh_test.log

✔ Portscan Grouped Simulation
for p in {20..40}; do
  echo "SYN scan detected from 33.33.33.33 on port $p" >> ~/logs/portscan_test.log
  sleep 0.1
done

✔ Web Attack Simulation (SQL Injection)
echo "192.168.1.10 GET /product?id=' OR '1'='1" >> ~/logs/web_test.log

📊 Screenshot (Dashboard)

(Add your own screenshot here)
To add:

![Dashboard Screenshot](screenshot.png)

📌 Future Enhancements

Add machine learning anomaly detection

Automatic IP blocking playbooks

Wazuh / Suricata log support

Cloud deployment

Docker packaging

👤 Author

Nawaz Muztaba
Cybersecurity Engineer
GitHub: https://github.com/NawazMuztaba

⭐ Support

If you like this project, please star ⭐ the repository!
