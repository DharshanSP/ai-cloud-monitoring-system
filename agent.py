import psutil
import time
import requests
import uuid
import argparse

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
# Replace this with the IP address of your Hub laptop
HUB_IP = "10.18.186.207" 
SERVER_URL = f"http://{HUB_IP}:5000/ingest"

# Unique identifier for this remote laptop
DEVICE_ID = f"remote-server-{uuid.uuid4().hex[:4]}"

# ==========================================
# 📊 METRIC COLLECTION LOGIC
# ==========================================
last_disk_bytes = psutil.disk_io_counters().read_bytes + psutil.disk_io_counters().write_bytes
last_net_bytes = psutil.net_io_counters().bytes_sent + psutil.net_io_counters().bytes_recv
last_check_time = time.time()

def get_metrics():
    global last_disk_bytes, last_net_bytes, last_check_time
    current_time = time.time()
    dt = current_time - last_check_time
    if dt < 0.1: dt = 0.1
    
    # Core Metrics
    cpu = psutil.cpu_percent()
    memory = psutil.virtual_memory().percent
    procs = len(psutil.pids())
    
    # I/O Metrics
    net_io = psutil.net_io_counters()
    disk_io = psutil.disk_io_counters()
    curr_disk = disk_io.read_bytes + disk_io.write_bytes
    curr_net = net_io.bytes_sent + net_io.bytes_recv
    
    # Calculate MB/s
    disk_mbs = ((curr_disk - last_disk_bytes) / dt) / (1024 * 1024)
    net_mbs = ((curr_net - last_net_bytes) / dt) / (1024 * 1024)
    
    last_disk_bytes = curr_disk
    last_net_bytes = curr_net
    last_check_time = current_time
    
    return {
        "device_id": DEVICE_ID,
        "cpu": cpu,
        "memory": memory,
        "disk": round(disk_mbs, 2),
        "network": round(net_mbs, 2),
        "processes": procs,
        "timestamp": current_time
    }

# ==========================================
# 🚀 EXECUTION LOOP
# ==========================================
print(f"[*] Starting AI Cloud Sentinel Agent...")
print(f"[*] Monitoring Device ID: {DEVICE_ID}")
print(f"[*] Sending metrics to Hub at: {SERVER_URL}")

# Initial call to prime psutil
psutil.cpu_percent()
time.sleep(1)

while True:
    try:
        metrics = get_metrics()
        response = requests.post(SERVER_URL, json=metrics, timeout=5)
        
        if response.status_code == 200:
            print(f"[✓] Metrics synced at {time.strftime('%H:%M:%S')} | CPU: {metrics['cpu']}% | MEM: {metrics['memory']}%")
        else:
            print(f"[!] Hub error (Status {response.status_code})")
            
    except requests.exceptions.ConnectionError:
        print(f"[X] Connection to Hub ({HUB_IP}) failed. Ensure the Hub is running and on the same network.")
    except Exception as e:
        print(f"[!] Agent error: {e}")
        
    time.sleep(2)
