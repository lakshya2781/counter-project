from flask import Flask, jsonify
import threading, time, datetime
from datetime import timezone, timedelta

app = Flask(__name__)

IST = timezone(timedelta(hours=5, minutes=30))

def now_ist():
    return datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

counter = {
    "value": 1,
    "logs": [],
    "start_time": now_ist(),
    "next_double_in": 180
}

LOG_FILE = "counter_log.txt"

def doubling_counter():
    while True:
        for remaining in range(180, 0, -1):
            counter["next_double_in"] = remaining
            time.sleep(1)
        counter["value"] *= 2
        timestamp = now_ist()
        log_entry = f"[{timestamp}] Counter doubled → {counter['value']}"
        counter["logs"].append(log_entry)
        with open(LOG_FILE, "a") as f:
            f.write(log_entry + "\n")
        print(log_entry, flush=True)

@app.route("/")
def home():
    logs_html = "<br>".join(counter["logs"][-20:]) or "Waiting for first double..."
    return f"""
    <html>
    <head><title>Counter Monitor</title><meta http-equiv="refresh" content="10"></head>
    <body style="font-family:monospace; background:#111; color:#0f0; padding:40px">
        <h2>Cloud Counter Monitor</h2>
        <p>Started (IST): {counter['start_time']}</p>
        <h1 style="font-size:4em; color:lime">{counter['value']}</h1>
        <p style="color:yellow">Next double in: {counter['next_double_in']} seconds</p>
        <hr>
        <h3>Logs (IST):</h3>
        <pre style="color:#0ff">{logs_html}</pre>
        <a href="/api" style="color:cyan">JSON API</a> | <a href="/logs" style="color:cyan">Raw Logs</a>
    </body></html>"""

@app.route("/api")
def api():
    return jsonify({
        "current_value": counter["value"],
        "next_double_in_seconds": counter["next_double_in"],
        "start_time_ist": counter["start_time"],
        "recent_logs": counter["logs"][-10:]
    })

@app.route("/logs")
def logs():
    try:
        with open(LOG_FILE) as f:
            return f"<pre style='background:#111;color:#0f0;padding:20px'>{f.read()}</pre>"
    except:
        return "<pre>No logs yet...</pre>"

if __name__ == "__main__":
    threading.Thread(target=doubling_counter, daemon=True).start()
    app.run(host="0.0.0.0", port=10000, threaded=True)
