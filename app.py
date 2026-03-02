from flask import Flask, jsonify, render_template
import time
import logging
import os
import psutil
import numpy as np
from sklearn.ensemble import IsolationForest
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

# ===============================
# Logging Setup
# ===============================
if not os.path.exists('logs'):
    os.makedirs('logs')

logging.basicConfig(
    filename='logs/app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ===============================
# In-Memory Metrics Storage
# ===============================
metrics_history = []
model = IsolationForest(contamination=0.05)

# ===============================
# Email Configuration
# ===============================
EMAIL_ADDRESS = "your_email@gmail.com"
EMAIL_PASSWORD = "your_app_password"   # Use Gmail App Password
ALERT_RECEIVER = "receiver_email@gmail.com"

def send_email_alert(cpu, memory):
    try:
        msg = MIMEText(f"""
⚠ AI ANOMALY DETECTED

CPU Usage: {cpu}%
Memory Usage: {memory}%

Check dashboard immediately.
""")

        msg['Subject'] = "AI Cloud Monitoring Alert"
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = ALERT_RECEIVER

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)

        logging.warning("Email alert sent.")

    except Exception as e:
        logging.error(f"Email failed: {e}")

# ===============================
# Routes
# ===============================

@app.route("/")
def dashboard():
    return render_template("index.html")

@app.route("/health")
def health():
    return jsonify({"status": "healthy"})

@app.route("/load")
def load():
    logging.warning("CPU load simulation triggered")
    x = 0
    for i in range(10**7):
        x += i
    return jsonify({"message": "CPU Load Generated"})

@app.route("/metrics")
def metrics():
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory().percent

    metrics_history.append([cpu, memory])

    if len(metrics_history) > 100:
        metrics_history.pop(0)

    anomaly_detected = False

    if len(metrics_history) > 30:
        data = np.array(metrics_history)
        model.fit(data)

        prediction = model.predict([[cpu, memory]])

        if prediction[0] == -1:
            anomaly_detected = True
            logging.warning("AI detected anomaly")
            send_email_alert(cpu, memory)

    return jsonify({
        "cpu": cpu,
        "memory": memory,
        "anomaly": anomaly_detected
    })

@app.route("/logs")
def get_logs():
    try:
        with open("logs/app.log", "r") as f:
            logs = f.readlines()[-20:]
        return jsonify({"logs": logs})
    except:
        return jsonify({"logs": []})

if __name__ == "__main__":
    app.run(debug=True)