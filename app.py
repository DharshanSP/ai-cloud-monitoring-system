from flask import Flask, jsonify, render_template, request, Response, send_file
import time
import logging
import os
import json
from datetime import datetime, timezone
import numpy as np
from sklearn.ensemble import IsolationForest
import requests
import threading
from dotenv import load_dotenv
from pymongo import MongoClient
from google import genai
import psutil

# ===============================
# 🔹 Environment Setup
# ===============================
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
EMAIL_TO = os.getenv("EMAIL_TO")

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
# 🔹 MongoDB Setup
# ===============================
try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_client.server_info() # trigger connection check
    db = mongo_client["ai_cloud_sentinel"]
    anomalies_collection = db["anomalies"]
    logging.info("Connected to MongoDB successfully.")
except Exception as e:
    logging.error(f"MongoDB connection failed: {e}")
    anomalies_collection = None

# ===============================
# 🔹 Gemini Setup
# ===============================
if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_key":
    genai_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    genai_client = None

# ===============================
# 🔹 System State
# ===============================
# Format: { "device_id": { history: [], model: IsolationForest, last_alert: 0, latest_anomaly: None, metrics: dict } }
devices_data = {}

def get_or_create_device(device_id):
    if device_id not in devices_data:
        devices_data[device_id] = {
            "history": [],
            "model": IsolationForest(contamination=0.08),
            "last_alert": 0,
            "latest_anomaly": None,
            "metrics": {}
        }
    return devices_data[device_id]

# ===============================
# 🔹 AI & Alerting
# ===============================
def check_anomaly_with_gemini(metrics_summary, rules_reason):
    if not genai_client:
        return fallback_reasoning(rules_reason)

    prompt = f"""
You are an expert AIOps Cloud Engineer. Analyze the recent metrics and the statistical anomaly triggers to determine the root cause, fix, and prevention.
Metrics Summary:
{metrics_summary}

Statistical Triggers:
{rules_reason}

Respond ONLY in valid JSON format with the following keys exactly:
{{
  "type": "CPU Spike | Memory Leak | Process Explosion | Disk Saturation | Network Spike | Unknown",
  "severity": "Warning | Critical",
  "reason": "Short human-readable explanation of what is happening",
  "root_cause": "Detailed technical root cause",
  "fix": "Step-by-step immediate actions to fix",
  "prevention": "Best practices to prevent this in the future"
}}
"""
    try:
        response = genai_client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        return json.loads(response.text)
    except Exception as e:
        logging.error(f"Gemini AI error: {e}")
        return fallback_reasoning(rules_reason)

def fallback_reasoning(rules_reason):
    return {
        "type": "System Anomaly",
        "severity": "Warning",
        "reason": f"Anomaly detected based on rules: {rules_reason}",
        "root_cause": "System metrics exceeded standard thresholds.",
        "fix": "Investigate running processes and check system logs.",
        "prevention": "Consider scaling resources or optimizing workloads."
    }

def send_email_alert(device_id, anomaly_data, metrics):
    if not RESEND_API_KEY or RESEND_API_KEY == "your_resend_key" or not EMAIL_TO:
        return
    
    subject = f"🚨 [{anomaly_data['severity'].upper()}] {anomaly_data['type']} Detected on {device_id} – AI Cloud Sentinel"
    
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; border: 1px solid #e2e8f0; border-radius: 10px; overflow: hidden;">
        <div style="background-color: #ff3366; color: white; padding: 20px; text-align: center;">
            <h2 style="margin: 0;">⚠ AI Anomaly Detected</h2>
            <p style="margin: 5px 0 0;">Device: {device_id}</p>
        </div>
        <div style="padding: 20px;">
            <h3 style="color: #1a202c; border-bottom: 2px solid #edf2f7; padding-bottom: 5px;">📊 Metrics at Time of Alert</h3>
            <ul>
                <li><b>CPU:</b> {metrics['cpu']}%</li>
                <li><b>Memory:</b> {metrics['memory']}%</li>
                <li><b>Disk I/O:</b> {metrics['disk']} MB/s</li>
                <li><b>Network I/O:</b> {metrics['network']} MB/s</li>
                <li><b>Processes:</b> {metrics['processes']}</li>
            </ul>
            <h3 style="color: #1a202c; border-bottom: 2px solid #edf2f7; padding-bottom: 5px;">🧠 What Happened</h3>
            <p>{anomaly_data['reason']}</p>
            <h3 style="color: #1a202c; border-bottom: 2px solid #edf2f7; padding-bottom: 5px;">⚠ Root Cause</h3>
            <p>{anomaly_data['root_cause']}</p>
            <h3 style="color: #1a202c; border-bottom: 2px solid #edf2f7; padding-bottom: 5px;">🔧 Fix</h3>
            <p>{anomaly_data['fix']}</p>
            <h3 style="color: #1a202c; border-bottom: 2px solid #edf2f7; padding-bottom: 5px;">🛡 Prevention</h3>
            <p>{anomaly_data['prevention']}</p>
        </div>
        <div style="background-color: #f7fafc; padding: 10px; text-align: center; font-size: 12px; color: #718096;">
            Time: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}<br>
            AI Cloud Sentinel – Hybrid AIOps Monitoring System
        </div>
    </div>
    """
    try:
        requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
            json={"from": "onboarding@resend.dev", "to": [EMAIL_TO], "subject": subject, "html": html_body}
        )
    except Exception as e:
        logging.error(f"Resend ERROR: {e}")

# ===============================
# 🔹 Anomaly Processing Engine
# ===============================
def process_device_metrics(device_id, data):
    device = get_or_create_device(device_id)
    device["metrics"] = data
    
    vec = [data['timestamp'], data['cpu'], data['memory'], data['disk'], data['network'], data['processes']]
    device["history"].append(vec)
    if len(device["history"]) > 300:
        device["history"].pop(0)

    reasons = []
    
    # 1. Hard Limits
    if data['cpu'] > 85: reasons.append("CPU > 85%")
    if data['memory'] > 90: reasons.append("Memory > 90%")
    if data['processes'] > 600: reasons.append("Processes > 600")
    
    # 2. Z-Score & Trend
    if len(device["history"]) > 30:
        history_np = np.array([h[1:] for h in device["history"]])
        curr_np = np.array(vec[1:])
        means = np.mean(history_np, axis=0)
        stds = np.std(history_np, axis=0)
        
        for i, metric_name in enumerate(["CPU", "Memory", "Disk", "Network", "Processes"]):
            if stds[i] > 0.1 and abs(curr_np[i] - means[i]) / stds[i] > 3.5:
                reasons.append(f"Statistically high {metric_name} spike")
        
        # Trend
        mem_data = history_np[-60:, 1]
        if len(mem_data) == 60:
            slope_mem = np.polyfit(np.arange(60), mem_data, 1)[0]
            if slope_mem > 0.1: reasons.append(f"Collective Anomaly: Memory Leak (slope={slope_mem:.3f})")
                
        proc_data = history_np[-60:, 4]
        if len(proc_data) == 60:
            slope_proc = np.polyfit(np.arange(60), proc_data, 1)[0]
            if slope_proc > 0.5: reasons.append(f"Collective Anomaly: Process Bloat (slope={slope_proc:.3f})")

        # 3. Isolation Forest ML
        try:
            device["model"].fit(history_np)
            if device["model"].predict([curr_np])[0] == -1:
                reasons.append("Complex Correlation Anomaly detected by ML")
        except:
            pass

    if reasons:
        if time.time() - device["last_alert"] > 120:
            device["last_alert"] = time.time()
            summary = "\n".join([f"CPU:{h[1]}% Mem:{h[2]}% Disk:{h[3]} Net:{h[4]} Procs:{h[5]}" for h in device["history"][-10:]])
            anomaly_data = check_anomaly_with_gemini(summary, " | ".join(reasons))
            
            anomaly_data["device_id"] = device_id
            anomaly_data["timestamp"] = datetime.now(timezone.utc).isoformat()
            for k in ['cpu', 'memory', 'disk', 'network', 'processes']:
                anomaly_data[k] = data[k]
                
            device["latest_anomaly"] = anomaly_data
            
            if anomalies_collection is not None:
                try: anomalies_collection.insert_one(anomaly_data.copy())
                except: pass
            
            # Email Alert
            threading.Thread(target=send_email_alert, args=(device_id, anomaly_data, data)).start()

# ===============================
# 🔹 Local Metrics Thread
# ===============================
def collect_local_metrics():
    last_disk_bytes = psutil.disk_io_counters().read_bytes + psutil.disk_io_counters().write_bytes
    last_net_bytes = psutil.net_io_counters().bytes_sent + psutil.net_io_counters().bytes_recv
    last_check_time = time.time()
    
    while True:
        start_measure = time.time()
        dt = start_measure - last_check_time
        if dt < 0.1: dt = 0.1
        
        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory().percent
        procs = len(psutil.pids())
        
        net_io = psutil.net_io_counters()
        disk_io = psutil.disk_io_counters()
        curr_disk = disk_io.read_bytes + disk_io.write_bytes
        curr_net = net_io.bytes_sent + net_io.bytes_recv
        disk_mbs = ((curr_disk - last_disk_bytes) / dt) / (1024 * 1024)
        net_mbs = ((curr_net - last_net_bytes) / dt) / (1024 * 1024)
        
        last_disk_bytes = curr_disk
        last_net_bytes = curr_net
        last_check_time = start_measure
        
        app_latency_ms = (time.time() - start_measure) * 1000
        
        data = {
            "device_id": "local-server",
            "timestamp": start_measure,
            "cpu": cpu,
            "memory": memory,
            "disk": round(disk_mbs, 2),
            "network": round(net_mbs, 2),
            "processes": procs,
            "latency": round(app_latency_ms, 2)
        }
        
        process_device_metrics("local-server", data)
        time.sleep(2)

threading.Thread(target=collect_local_metrics, daemon=True).start()

# ===============================
# 🔹 Routes
# ===============================
@app.route("/")
def dashboard():
    return render_template("index.html")

@app.route("/task-manager")
def task_manager():
    return render_template("task_manager.html")

@app.route("/api/processes")
def api_processes():
    processes = []
    # Fetch top processes using psutil
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
        try:
            info = p.info
            processes.append({
                "pid": info['pid'],
                "name": info['name'],
                "cpu": info['cpu_percent'] or 0.0,
                "memory": info['memory_percent'] or 0.0,
                "status": info['status']
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    # Sort by CPU usage descending and grab top 50
    processes = sorted(processes, key=lambda x: x['cpu'], reverse=True)[:50]
    return jsonify({"processes": processes})

@app.route("/health")
def health():
    return jsonify({"status": "healthy", "devices": len(devices_data), "db_connected": anomalies_collection is not None})

@app.route("/devices")
def list_devices():
    return jsonify({"devices": list(devices_data.keys())})

@app.route("/device/<device_id>/metrics")
def get_device_metrics(device_id):
    if device_id not in devices_data:
        return jsonify({"error": "Device not found"}), 404
        
    device = devices_data[device_id]
    if "cpu" not in device["metrics"]:
        return jsonify({"error": "No data yet"}), 404
        
    metrics = device["metrics"].copy()
    
    # Send anomaly context to UI if recent (within 60s)
    metrics["anomaly"] = False
    if device["latest_anomaly"] and (time.time() - device["last_alert"] < 60):
        metrics["anomaly"] = True
        metrics["anomaly_data"] = device["latest_anomaly"]
        
    return jsonify(metrics)

@app.route("/predict/<device_id>")
def predict_incident(device_id):
    if device_id not in devices_data:
        return jsonify({"error": "Device not found"}), 404
        
    device = devices_data[device_id]
    history = device["history"]
    
    if len(history) < 20:
        return jsonify({"prediction": "Insufficient data for forecasting", "confidence": 0})

    # Use last 60 points for trend
    data_window = np.array(history[-60:])
    timestamps = data_window[:, 0] - data_window[0, 0] # relative time
    cpu_data = data_window[:, 1]
    mem_data = data_window[:, 2]

    # 1. Exponential Smoothing (EMA) for current baseline
    def get_ema(data, alpha=0.3):
        ema = [data[0]]
        for i in range(1, len(data)):
            ema.append(alpha * data[i] + (1 - alpha) * ema[-1])
        return ema[-1]

    curr_cpu_ema = get_ema(cpu_data)
    curr_mem_ema = get_ema(mem_data)

    # 2. Linear Regression for Trend Prediction
    from sklearn.linear_model import LinearRegression
    X = timestamps.reshape(-1, 1)
    
    # CPU Prediction
    model_cpu = LinearRegression().fit(X, cpu_data)
    cpu_slope = model_cpu.coef_[0]
    
    # Memory Prediction
    model_mem = LinearRegression().fit(X, mem_data)
    mem_slope = model_mem.coef_[0]

    # Calculate Time to 95% threshold
    # y = mx + b  => x = (95 - b) / m
    prediction = "System Stable"
    time_to_incident = -1
    risk_level = "Low"
    
    # Check if trending upwards
    if cpu_slope > 0.01: # Trending up
        ttf_cpu = (95 - curr_cpu_ema) / cpu_slope if cpu_slope > 0 else 9999
        if ttf_cpu > 0 and ttf_cpu < 3600: # within an hour
            prediction = f"Potential CPU Exhaustion in ~{int(ttf_cpu/60)} mins"
            time_to_incident = ttf_cpu
            risk_level = "High" if ttf_cpu < 600 else "Medium"

    if mem_slope > 0.01:
        ttf_mem = (95 - curr_mem_ema) / mem_slope if mem_slope > 0 else 9999
        if ttf_mem > 0 and (time_to_incident == -1 or ttf_mem < time_to_incident):
            prediction = f"Memory Critical threshold in ~{int(ttf_mem/60)} mins"
            time_to_incident = ttf_mem
            risk_level = "High" if ttf_mem < 600 else "Medium"

    return jsonify({
        "prediction": prediction,
        "time_to_incident": round(time_to_incident, 1),
        "risk_level": risk_level,
        "cpu_slope": round(cpu_slope, 4),
        "mem_slope": round(mem_slope, 4),
        "current_trends": {
            "cpu_ema": round(curr_cpu_ema, 2),
            "mem_ema": round(curr_mem_ema, 2)
        }
    })

@app.route("/ingest", methods=["POST"])
def ingest():
    data = request.json
    device_id = data.get("device_id")
    if not device_id:
        return jsonify({"error": "No device_id"}), 400
    
    # Optional app latency override
    if "latency" not in data:
        data["latency"] = 0
        
    process_device_metrics(device_id, data)
    return jsonify({"status": "ok"})

@app.route("/download-agent")
def download_agent():
    # Dynamically inject the server's host IP into the agent script
    server_ip = request.host
    agent_code = f"""import psutil
import time
import requests
import uuid
import argparse

SERVER_URL = "http://{server_ip}/ingest"
DEVICE_ID = f"server-{{uuid.uuid4().hex[:4]}}"

last_disk_bytes = psutil.disk_io_counters().read_bytes + psutil.disk_io_counters().write_bytes
last_net_bytes = psutil.net_io_counters().bytes_sent + psutil.net_io_counters().bytes_recv
last_check_time = time.time()

def get_metrics():
    global last_disk_bytes, last_net_bytes, last_check_time
    current_time = time.time()
    dt = current_time - last_check_time
    if dt < 0.1: dt = 0.1
    
    cpu = psutil.cpu_percent()
    memory = psutil.virtual_memory().percent
    procs = len(psutil.pids())
    
    net_io = psutil.net_io_counters()
    disk_io = psutil.disk_io_counters()
    curr_disk = disk_io.read_bytes + disk_io.write_bytes
    curr_net = net_io.bytes_sent + net_io.bytes_recv
    disk_mbs = ((curr_disk - last_disk_bytes) / dt) / (1024 * 1024)
    net_mbs = ((curr_net - last_net_bytes) / dt) / (1024 * 1024)
    
    last_disk_bytes = curr_disk
    last_net_bytes = curr_net
    last_check_time = current_time
    
    return {{
        "device_id": DEVICE_ID,
        "cpu": cpu,
        "memory": memory,
        "disk": round(disk_mbs, 2),
        "network": round(net_mbs, 2),
        "processes": procs,
        "timestamp": current_time
    }}

print(f"[*] Starting AI Cloud Sentinel Agent on device: {{DEVICE_ID}}")
print(f"[*] Sending metrics to: {{SERVER_URL}}")

psutil.cpu_percent()
time.sleep(1)

while True:
    try:
        metrics = get_metrics()
        response = requests.post(SERVER_URL, json=metrics, timeout=5)
        if response.status_code != 200:
            print(f"[!] Server returned status: {{response.status_code}}")
    except requests.exceptions.ConnectionError:
        print(f"[X] Connection to {{SERVER_URL}} failed. Retrying...")
    except Exception as e:
        print(f"[!] Agent error: {{e}}")
    time.sleep(2)
"""
    return Response(agent_code, mimetype="text/plain", headers={"Content-Disposition": "attachment;filename=agent.py"})

@app.route("/history")
def get_history():
    if anomalies_collection is not None:
        try:
            docs = list(anomalies_collection.find({}, {"_id": 0}).sort("timestamp", -1).limit(50))
            return jsonify({"history": docs})
        except: pass
    return jsonify({"history": []})

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
    return jsonify({"message": "Load Generated"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False, threaded=True)