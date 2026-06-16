from flask import Flask, jsonify
import threading, time, datetime

app = Flask(__name__)

counter = {
    "value": 1,
    "logs": [],
    "start_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}

LOG_FILE = "counter_log.txt"

def doubling_counter():
    while True:
        time.sleep(180)  # 3 minutes
        counter["value"] *= 2
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] Counter doubled → {counter['value']}"
        counter["logs"].append(log_entry)
        with open(LOG_FILE, "a") as f:
            f.write(log_entry + "\n")
        print(log_entry)

@app.route("/")
def home():
    logs_html = "<br>".join(counter["logs"][-20:]) or "⏳ Waiting for first double (3 mins)..."
    return f"""
    <html>
    <head>
        <title>Counter Monitor</title>
        <meta http-equiv="refresh" content="30">
    </head>
    <body style="font-family:monospace; background:#111; color:#0f0; padding:40px">
        <h2>🖥️ Cloud Counter Monitor</h2>
        <p>🕐 Started: {counter['start_time']}</p>
        <hr>
        <p>Current Value:</p>
        <h1 style="font-size:4em; color:lime">{counter['value']}</h1>
        <p style="color:#aaa">(doubles every 3 minutes)</p>
        <hr>
        <h3>📋 Logs:</h3>
        <pre style="color:#0ff">{logs_html}</pre>
        <br>
        <a href="/api" style="color:cyan">📡 JSON API</a> &nbsp;|&nbsp;
        <a href="/logs" style="color:cyan">📄 Raw Logs</a>
    </body>
    </html>"""

@app.route("/api")
def api():
    return jsonify({
        "current_value": counter["value"],
        "start_time": counter["start_time"],
        "total_doubles": len(counter["logs"]),
        "recent_logs": counter["logs"][-10:]
    })

@app.route("/logs")
def logs():
    try:
        with open(LOG_FILE) as f:
            return f"<pre style='background:#111;color:#0f0;padding:20px'>{f.read()}</pre>"
    except:
        return "<pre>No logs yet... check back in 3 minutes!</pre>"

if __name__ == "__main__":
    threading.Thread(target=doubling_counter, daemon=True).start()
    app.run(host="0.0.0.0", port=10000)