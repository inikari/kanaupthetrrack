import psutil
import time
import json
import os
from datetime import datetime
import requests
import subprocess

MONITORING_URL = "http://<server-monitoring-ip>:5000/agent-data"

# Paths
LOG_FILE = "logs/error_log.json"
SPECS_FILE = "data/specs.json"

def get_specs():
    specs = {
        "cpu": {
            "model": subprocess.check_output("cat /proc/cpuinfo | grep 'model name' | uniq", shell=True).decode().strip(),
            "cores": psutil.cpu_count(logical=False),
            "threads": psutil.cpu_count(logical=True),
        },
        "ram": {
            "total_gb": round(psutil.virtual_memory().total / (1024**3), 2)
        },
        "gpu": get_gpu_info(),
        "disk": {
            "total_gb": round(psutil.disk_usage('/').total / (1024**3), 2)
        }
    }
    with open(SPECS_FILE, "w") as f:
        json.dump(specs, f)
    return specs

def get_gpu_info():
    try:
        nvidia_smi_output = subprocess.check_output(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], encoding="utf-8")
        gpus = [{"name": gpu.split(",")[0], "vram": gpu.split(",")[1]} for gpu in nvidia_smi_output.strip().split("\n")]
    except Exception:
        gpus = []
    return gpus

def monitor():
    while True:
        data = {
            "cpu": {
                "usage_per_core": psutil.cpu_percent(interval=1, percpu=True),
                "usage_total": psutil.cpu_percent(interval=1),
                "temp": get_cpu_temp(),
            },
            "ram": {
                "usage_percent": psutil.virtual_memory().percent,
                "usage_gb": round(psutil.virtual_memory().used / (1024**3), 2)
            },
            "gpu": get_gpu_usage(),
            "log_errors": get_network_status(),
        }
        try:
            requests.post(MONITORING_URL, json=data)
        except Exception as e:
            log_error("Failed to send data: " + str(e))
        time.sleep(300)

def get_cpu_temp():
    try:
        temp_output = subprocess.check_output(["sensors"], encoding="utf-8")
        temp_line = [line for line in temp_output.split("\n") if "Package id 0:" in line][0]
        temp = float(temp_line.split(":")[1].strip().split("°C")[0])
        return temp
    except Exception:
        return None

def get_gpu_usage():
    try:
        nvidia_smi_output = subprocess.check_output(["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu", "--format=csv,noheader"], encoding="utf-8")
        gpu_usage = [{"usage": gpu.split(",")[0], "temp": gpu.split(",")[1]} for gpu in nvidia_smi_output.strip().split("\n")]
    except Exception:
        gpu_usage = []
    return gpu_usage

def get_network_status():
    try:
        ping_output = subprocess.check_output(["ping", "-c", "1", "google.com"])
        return []
    except Exception as e:
        log_error("Network issue: " + str(e))
        return ["Network issue"]

def log_error(error_message):
    log = {
        "timestamp": datetime.now().isoformat(),
        "error": error_message
    }
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            json.dump([log], f)
    else:
        with open(LOG_FILE, "r") as f:
            logs = json.load(f)
        logs.append(log)
        with open(LOG_FILE, "w") as f:
            json.dump(logs, f)

if __name__ == "__main__":
    get_specs()
    monitor()
