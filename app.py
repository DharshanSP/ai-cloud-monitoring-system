from flask import Flask, jsonify, render_template, request
import time
import logging
import os
import psutil
import numpy as np
from sklearn.ensemble import IsolationForest
import requests

# ✅ Gemini NEW SDK
from google import genai

app = Flask(__name__)

# ===============================
# 🔹 Logging Setup
# ===============================
if not os.path.exists('logs'):
    os.makedirs('logs')

logging.basicConfig(
    filename='logs/app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ===============================
# 🔹 Gemini Setup
# ===============================
GEMINI_API_KEY = "AIzaSyD1beA-eC5qC34isQ6xdFH_LXySCChYaNw"
client = genai.Client(api_key=GEMINI_API_KEY)

# ===============================
# 🔹 Local AI Setup
# ===============================
metrics_history = []
model_local = IsolationForest(contamination=0.05)

# ===============================
# 🔹 Resend API Setup
# ===============================
RESEND_API_KEY = "re_TuZwzy55_2RjUcGfk4Sgefv3sqmy4vp9a"

def send_email_alert(cpu, memory, reason):
    try:
        print("Sending email via Resend...")

        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "from": "onboarding@resend.dev",
                "to": ["s.p.darshan0417@gmail.com"],  # 🔴 change this
                "subject": "🚨 AI Monitoring Alert",
                "html": f"""
                <h2>⚠ AI Anomaly Detected</h2>
                <p><b>CPU:</b> {cpu}%</p>
                <p><b>Memory:</b> {memory}%</p>
                <p><b>Reason:</b> {reason}</p>
                """
            }
        )

        print("Resend response:", response.status_code, response.text)

    except Exception as e:
        print("Resend ERROR:", e)

# ===============================
# 🔹 Gemini AI Function
# ===============================
def check_anomaly_with_gemini(cpu, memory):
    try:
        prompt = f"""
You are an AI cloud monitoring system.

CPU Usage: {cpu}%
Memory Usage: {memory}%

Is this abnormal? Answer YES or NO and give short reason.
"""

        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )

        text = response.text.lower()

        if "yes" in text:
            return True, text
        return False, text

    except Exception as e:
        logging.error(f"Gemini error: {e}")
        return False, "AI error"

# ===============================
# 🔹 Routes
# ===============================

@app.route("/")
def dashboard():
    return render_template("index.html")

@app.route("/health")
def health():
    return jsonify({"status": "healthy"})

@app.route("/load")
def load():
    logging.warning("CPU load triggered")
    x = 0
    for i in range(10**7):
        x += i
    return jsonify({"message": "CPU Load Generated"})

@app.route("/metrics")
def metrics():
    mode = request.args.get("mode", "local")

    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory().percent

    anomaly_detected = False
    reason = "System Normal"

    # ===============================
    # LOCAL AI
    # ===============================
    if mode == "local":
        metrics_history.append([cpu, memory])

        if len(metrics_history) > 100:
            metrics_history.pop(0)

        if len(metrics_history) > 30:
            data = np.array(metrics_history)
            model_local.fit(data)

            prediction = model_local.predict([[cpu, memory]])

            if prediction[0] == -1:
                anomaly_detected = True
                reason = "Local AI detected unusual pattern"

    # ===============================
    # GEMINI AI
    # ===============================
    else:
        if cpu > 85:
            anomaly_detected = True
            reason = "Critical CPU spike detected"
        elif cpu > 60:
            anomaly_detected, reason = check_anomaly_with_gemini(cpu, memory)

    # ===============================
    # ALERT
    # ===============================
    if anomaly_detected:
        send_email_alert(cpu, memory, reason)
        logging.warning(f"Anomaly detected: {reason}")

    return jsonify({
        "cpu": cpu,
        "memory": memory,
        "anomaly": anomaly_detected,
        "reason": reason,
        "mode": mode
    })

@app.route("/logs")
def get_logs():
    try:
        with open("logs/app.log", "r") as f:
            logs = f.readlines()[-20:]
        return jsonify({"logs": logs})
    except:
        return jsonify({"logs": []})

# ===============================
# 🔹 Run App
# ===============================
if __name__ == "__main__":
    app.run(debug=True)