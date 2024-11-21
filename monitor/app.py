from flask import Flask, render_template, request, jsonify
import json
from datetime import datetime

app = Flask(__name__)

# Paths
SERVERS_DB = "data/servers.json"
LOGS_DB = "data/logs.json"

# Load or initialize databases
def load_json(path, default):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        with open(path, "w") as f:
            json.dump(default, f)
        return default

servers = load_json(SERVERS_DB, [])
logs = load_json(LOGS_DB, [])

# Save data to JSON
def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

# Route to receive data from agent
@app.route("/agent-data", methods=["POST"])
def agent_data():
    data = request.json
    agent_ip = request.remote_addr
    timestamp = datetime.now().isoformat()
    
    # Find or add server entry
    server = next((s for s in servers if s["ip"] == agent_ip), None)
    if server is None:
        server = {"ip": agent_ip, "last_update": timestamp, "data": data}
        servers.append(server)
    else:
        server["last_update"] = timestamp
        server["data"] = data
    
    # Save logs if error exists
    if "log_errors" in data and data["log_errors"]:
        for error in data["log_errors"]:
            logs.append({"ip": agent_ip, "timestamp": timestamp, "error": error})
        save_json(LOGS_DB, logs)

    # Save servers
    save_json(SERVERS_DB, servers)
    return jsonify({"status": "success"})

# Dashboard page
@app.route("/")
def dashboard():
    return render_template("dashboard.html", servers=servers)

# Server detail page
@app.route("/server/<ip>")
def server_detail(ip):
    server = next((s for s in servers if s["ip"] == ip), None)
    if server is None:
        return "Server not found", 404
    server_logs = [log for log in logs if log["ip"] == ip]
    return render_template("server.html", server=server, logs=server_logs[:3])

# Specs, CPU, GPU, RAM, and Log pages
@app.route("/server/<ip>/<section>")
def server_section(ip, section):
    server = next((s for s in servers if s["ip"] == ip), None)
    if server is None:
        return "Server not found", 404
    if section == "log":
        server_logs = [log for log in logs if log["ip"] == ip]
        return render_template("log.html", logs=server_logs)
    return render_template(f"{section}.html", server=server)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
