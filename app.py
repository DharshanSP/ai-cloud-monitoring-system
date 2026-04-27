from flask import Flask, jsonify, render_template, request
import time
import logging
import os
import json
from datetime import datetime
import psutil
import numpy as np
from sklearn.ensemble import IsolationForest
import requests
from pymongo import DESCENDING, MongoClient
from pymongo.errors import PyMongoError

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
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# ===============================
# 🔹 Local AI & Baseline Setup
# ===============================
# Format: [timestamp, cpu, memory, disk_mbs, net_mbs, proc_count, latency_ms]
metrics_history = []
last_disk_bytes = psutil.disk_io_counters().read_bytes + psutil.disk_io_counters().write_bytes
last_net_bytes = psutil.net_io_counters().bytes_sent + psutil.net_io_counters().bytes_recv
last_check_time = time.time()

# Baseline for Behavioral/Seasonal Analysis
BASELINE_FILE = 'baseline.json'
if os.path.exists(BASELINE_FILE):
    with open(BASELINE_FILE, 'r') as f:
        baseline_data = json.load(f)
else:
    # 24 buckets (hours) x metrics
    baseline_data = {str(h): {"cpu": 20, "memory": 40, "disk": 1, "net": 0.5, "proc": 300, "count": 1} for h in range(24)}

def update_baseline(hour, metrics_vec):
    h_str = str(hour)
    b = baseline_data[h_str]
    # Simple running average for baseline
    alpha = 0.05
    b["cpu"] = (1 - alpha) * b["cpu"] + alpha * metrics_vec[0]
    b["memory"] = (1 - alpha) * b["memory"] + alpha * metrics_vec[1]
    b["disk"] = (1 - alpha) * b["disk"] + alpha * metrics_vec[2]
    b["net"] = (1 - alpha) * b["net"] + alpha * metrics_vec[3]
    b["proc"] = (1 - alpha) * b["proc"] + alpha * metrics_vec[4]
    b["count"] += 1
    
    # Save every 10 updates to avoid disk thrashing
    if b["count"] % 10 == 0:
        with open(BASELINE_FILE, 'w') as f:
            json.dump(baseline_data, f)

model_local = IsolationForest(contamination=0.08)

# ===============================
# 🔹 Resend API Setup
# ===============================
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "your_email@gmail.com")

# ===============================
# MongoDB Setup
# ===============================
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "ai_cloud_monitor")

anomalies_collection = None
try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    mongo_client.admin.command("ping")
    mongo_db = mongo_client[MONGO_DB_NAME]
    anomalies_collection = mongo_db["anomalies"]
    anomalies_collection.create_index([("timestamp", DESCENDING)])
    logging.info("MongoDB connected successfully.")
except Exception as e:
    logging.warning(f"MongoDB unavailable. Running without anomaly persistence: {e}")
    anomalies_collection = None


def store_anomaly(record):
    if anomalies_collection is None:
        return
    try:
        anomalies_collection.insert_one(record)
    except PyMongoError as e:
        logging.error(f"Failed to store anomaly in MongoDB: {e}")

def send_email_alert(cpu, memory, reason):
    if not RESEND_API_KEY:
        return
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
                "to": [ALERT_EMAIL_TO],
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
# 🔹 Gemini AI Function (Enhanced)
# ===============================
def check_anomaly_with_gemini(recent_metrics):
    if client is None:
        return False, "Gemini not configured"
    try:
        # Convert metrics to a human-readable summary
        summary = "\n".join([
            f"T-{len(recent_metrics)-i}s: CPU={m[0]}%, Mem={m[1]}%, Disk={m[2]:.1f}MB/s, Net={m[3]:.1f}MB/s"
            for i, m in enumerate(recent_metrics[-10:])
        ])

        prompt = f"""
You are a Cloud Infrastructure Expert. Analyze the following 10-second performance window:

{summary}

Identify if there is any anomaly. Categorize it as:
- 'Point' (spike)
- 'Trend' (gradual increase, leak)
- 'Correlation' (unusual relationship)
- 'None' (normal)

Answer in JSON format:
{{
  "anomaly": true/false,
  "category": "...",
  "reason": "..."
}}
"""
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
            }
        )
        
        import json
        result = json.loads(response.text)
        return result.get("anomaly", False), result.get("reason", "Unknown AI analysis")

    except Exception as e:
        logging.error(f"Gemini error: {e}")
        return False, "AI context error"

def calculate_z_score_anomalies(current_metrics, history):
    if len(history) < 20:
        return []
    
    anomalies = []
    data = np.array(history)
    means = np.mean(data, axis=0)
    stds = np.std(data, axis=0)
    
    # Check CPU, Mem, Disk, Net
    labels = ["CPU", "Memory", "Disk I/O", "Network I/O"]
    threshold = 3.0 # Standard z-score threshold
    
    for i in range(len(labels)):
        if stds[i] > 0.1: # Avoid division by zero
            z = abs(current_metrics[i] - means[i]) / stds[i]
            if z > threshold:
                anomalies.append(f"Statistically high {labels[i]} (z={z:.1f})")
    
    return anomalies

def detect_trends(history):
    if len(history) < 60:
        return []
    
    anomalies = []
    data = np.array(history[-60:])
    
    # Check for memory leaks
    mem_data = data[:, 1]
    slope_mem = np.polyfit(np.arange(len(mem_data)), mem_data, 1)[0]
    if slope_mem > 0.1:
        anomalies.append(f"Collective Anomaly: Memory Leak (slope={slope_mem:.3f})")

    # Check for process bloating
    proc_data = data[:, 4]
    slope_proc = np.polyfit(np.arange(len(proc_data)), proc_data, 1)[0]
    if slope_proc > 0.5:
        anomalies.append(f"Collective Anomaly: Process Count Bloating (slope={slope_proc:.3f})")
        
    return anomalies

def detect_behavioral_anomalies(current_vec):
    hour = datetime.now().hour
    baseline = baseline_data[str(hour)]
    anomalies = []
    
    # Compare CPU/Net against time-of-day baseline
    if current_vec[0] > baseline["cpu"] * 2.5 and baseline["cpu"] > 5:
        anomalies.append(f"Behavioral Anomaly: CPU unusually high for this hour ({current_vec[0]:.1f}% vs typical {baseline['cpu']:.1f}%)")
    
    if current_vec[3] > baseline["net"] * 5 and baseline["net"] > 0.1:
        anomalies.append(f"Behavioral Anomaly: Network traffic spike for this hour")
        
    return anomalies

# ===============================
# 🔹 Routes
# ===============================
@app.route("/")
def dashboard():
    return render_template("index.html")

@app.route("/health")
def health():
    return jsonify({"status": "healthy", "baseline_entries": sum([b["count"] for b in baseline_data.values()])})

@app.route("/load")
def load():
    type = request.args.get("type", "cpu")
    if type == "cpu":
        logging.warning("Manual CPU load spike triggered")
        for i in range(10**7): pass
        return jsonify({"message": "CPU Spike Generated"})
    elif type == "mem":
        logging.warning("Manual Memory leak triggered")
        global leak_array
        if 'leak_array' not in globals(): leak_array = []
        leak_array.append([0] * 10**6) # Leak 8MB
        return jsonify({"message": "Memory Leak Simulated"})
    elif type == "proc":
        logging.warning("Manual Process spike sparked")
        import subprocess
        for _ in range(5): subprocess.Popen(["cmd", "/c", "timeout 5"], shell=True)
        return jsonify({"message": "Process spike triggered"})
    return jsonify({"message": "Generic Load Generated"})

@app.route("/metrics")
def metrics():
    start_measure = time.time()
    global last_disk_bytes, last_net_bytes, last_check_time
    mode = request.args.get("mode", "local")

    current_time = time.time()
    dt = current_time - last_check_time
    if dt < 0.1: dt = 0.1

    # Basic Metrics
    cpu = psutil.cpu_percent()
    memory = psutil.virtual_memory().percent
    procs = len(psutil.pids())
    
    # IO Metrics
    net_io = psutil.net_io_counters()
    disk_io = psutil.disk_io_counters()
    curr_disk = disk_io.read_bytes + disk_io.write_bytes
    curr_net = net_io.bytes_sent + net_io.bytes_recv
    disk_mbs = ((curr_disk - last_disk_bytes) / dt) / (1024 * 1024)
    net_mbs = ((curr_net - last_net_bytes) / dt) / (1024 * 1024)
    
    # State update
    last_disk_bytes = curr_disk
    last_net_bytes = curr_net
    last_check_time = current_time
    
    # App Latency measure (end of gathering)
    app_latency_ms = (time.time() - start_measure) * 1000

    current_vec = [cpu, memory, disk_mbs, net_mbs, procs, app_latency_ms]
    
    # Baseline update
    update_baseline(datetime.now().hour, current_vec)
    
    anomaly_detected = False
    reasons = []
    
    # ===============================
    # MULTI-LAYER DETECTION
    # ===============================
    
    # 1. Point Anomalies (Z-Score)
    z_anomalies = calculate_z_score_anomalies(current_vec[:4], [h[1:5] for h in metrics_history])
    reasons.extend(z_anomalies)
    
    # 2. Collective/Trend Anomalies
    t_anomalies = detect_trends([h[1:] for h in metrics_history])
    reasons.extend(t_anomalies)

    # 3. Behavioral/Seasonal Anomalies
    b_anomalies = detect_behavioral_anomalies(current_vec)
    reasons.extend(b_anomalies)

    # 4. App-Level / Resource Hard Limits
    if app_latency_ms > 200:
        reasons.append(f"Application Anomaly: High monitoring latency ({app_latency_ms:.1f}ms)")
    if procs > 500:
        reasons.append(f"Process Anomaly: Excessive system processes ({procs})")

    # 5. Multivariate Correlation
    if len(metrics_history) > 30:
        data = np.array([h[1:] for h in metrics_history])
        model_local.fit(data)
        prediction = model_local.predict([current_vec])
        if prediction[0] == -1:
            reasons.append("Complex Correlation Anomaly detected")

    # Gemini Refinement... (clipped for brevity, logic remains same but passes full vec)
    ai_feedback = ""
    if mode == "gemini":
        if len(reasons) > 0 or cpu > 70 or memory > 85:
             gemini_anomaly, gemini_reason = check_anomaly_with_gemini([h[1:] for h in metrics_history] + [current_vec])
             if gemini_anomaly:
                 anomaly_detected = True
                 ai_feedback = gemini_reason
             else:
                 ai_feedback = f"System under pressure, but Gemini verifies it as normal context."
    else:
        if len(reasons) > 0:
            anomaly_detected = True
            ai_feedback = " | ".join(reasons)
        else:
            ai_feedback = "System Normal"

    metrics_history.append([current_time] + current_vec)
    if len(metrics_history) > 300: metrics_history.pop(0)

    if anomaly_detected:
        send_email_alert(cpu, memory, ai_feedback)
        logging.warning(f"ANOMALY: {ai_feedback}")
        store_anomaly({
            "timestamp": datetime.utcnow(),
            "mode": mode,
            "reason": ai_feedback,
            "metrics": {
                "cpu": round(cpu, 2),
                "memory": round(memory, 2),
                "disk": round(disk_mbs, 2),
                "network": round(net_mbs, 2),
                "processes": int(procs),
                "latency_ms": round(app_latency_ms, 2)
            }
        })

    return jsonify({
        "cpu": cpu, "memory": memory, "disk": round(disk_mbs, 2), "net": round(net_mbs, 2),
        "procs": procs, "latency": round(app_latency_ms, 2),
        "anomaly": anomaly_detected, "reason": ai_feedback, "mode": mode
    })

@app.route("/logs")
def get_logs():
    try:
        with open("logs/app.log", "r") as f:
            logs = f.readlines()[-20:]
        return jsonify({"logs": logs})
    except:
        return jsonify({"logs": []})


@app.route("/anomalies")
def get_anomalies():
    limit = request.args.get("limit", 20, type=int)
    limit = min(max(limit, 1), 100)

    if anomalies_collection is None:
        return jsonify({"anomalies": [], "storage": "unavailable"})

    try:
        docs = anomalies_collection.find({}, {"_id": 0}).sort("timestamp", DESCENDING).limit(limit)
        anomalies = []
        for d in docs:
            ts = d.get("timestamp")
            if hasattr(ts, "isoformat"):
                d["timestamp"] = ts.isoformat() + "Z"
            anomalies.append(d)
        return jsonify({"anomalies": anomalies, "storage": "mongodb"})
    except PyMongoError as e:
        logging.error(f"Failed to fetch anomalies: {e}")
        return jsonify({"anomalies": [], "storage": "error"})

# ===============================
# 🔹 Run App
# ===============================
if __name__ == "__main__":
    app.run(debug=True)