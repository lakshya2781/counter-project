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
    return """
    <html>
    <head>
        <title>Counter Monitor</title>
        <style>
            body { font-family:monospace; background:#111; color:#0f0; padding:40px; }
            #value { font-size:4em; color:lime; }
            #countdown { color:yellow; }
            pre { color:#0ff; }
        </style>
    </head>
    <body>
        <h2>🖥️ Cloud Counter Monitor</h2>
        <p>Started (IST): <span id="start_time">loading...</span></p>
        <div id="value">--</div>
        <p>Next double in: <span id="countdown">--</span> seconds</p>
        <hr>
        <h3>📋 Logs:</h3>
        <pre id="logs">loading...</pre>

        <script>
        async function updateData() {
            const res = await fetch('/api');
            const data = await res.json();
            document.getElementById('value').innerText = data.current_value;
            document.getElementById('countdown').innerText = data.next_double_in_seconds;
            document.getElementById('start_time').innerText = data.start_time_ist;
            document.getElementById('logs').innerText = data.recent_logs.join('\\n') || 'Waiting for first double...';
        }
        updateData();              // run once immediately
        setInterval(updateData, 2000);   // then every 2 seconds, no page reload
        </script>
    </body></html>"""

@app.route("/api")
def api():
    return jsonify({
        "current_value": counter["value"],
        "next_double_in_seconds": counter["next_double_in"],
        "start_time_ist": counter["start_time"],
        "recent_logs": counter["logs"][-10:]
    })

if __name__ == "__main__":
    threading.Thread(target=doubling_counter, daemon=True).start()
    app.run(host="0.0.0.0", port=10000, threaded=True)
