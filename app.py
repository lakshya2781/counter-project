from flask import Flask, jsonify
import threading, time, datetime, os
from datetime import timezone, timedelta
import psycopg2

app = Flask(__name__)

IST = timezone(timedelta(hours=5, minutes=30))
def now_ist():
    return datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS counter_state (
            id INTEGER PRIMARY KEY DEFAULT 1,
            value BIGINT NOT NULL,
            start_time TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS counter_logs (
            id SERIAL PRIMARY KEY,
            log_time TEXT NOT NULL,
            value BIGINT NOT NULL
        )
    """)
    # Insert initial row if not exists
    cur.execute("SELECT COUNT(*) FROM counter_state")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO counter_state (id, value, start_time) VALUES (1, 1, %s)", (now_ist(),))
    conn.commit()
    cur.close()
    conn.close()

def get_state():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT value, start_time FROM counter_state WHERE id=1")
    value, start_time = cur.fetchone()
    cur.execute("SELECT log_time, value FROM counter_logs ORDER BY id DESC LIMIT 10")
    logs = [f"[{t}] Counter doubled → {v}" for t, v in cur.fetchall()]
    cur.close()
    conn.close()
    return value, start_time, list(reversed(logs))

def double_value():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT value FROM counter_state WHERE id=1")
    value = cur.fetchone()[0] * 2
    cur.execute("UPDATE counter_state SET value=%s WHERE id=1", (value,))
    cur.execute("INSERT INTO counter_logs (log_time, value) VALUES (%s, %s)", (now_ist(), value))
    conn.commit()
    cur.close()
    conn.close()
    return value

next_double_in = {"seconds": 180}

def doubling_counter():
    while True:
        for remaining in range(180, 0, -1):
            next_double_in["seconds"] = remaining
            time.sleep(1)
        new_value = double_value()
        print(f"[{now_ist()}] Counter doubled → {new_value}", flush=True)

@app.route("/")
def home():
    return """
    <html>
    <head>
        <title>Counter Monitor</title>
        <style>body{font-family:monospace;background:#111;color:#0f0;padding:40px;}
        #value{font-size:4em;color:lime;} #countdown{color:yellow;} pre{color:#0ff;}</style>
    </head>
    <body>
        <h2>🖥️ Cloud Counter Monitor (Persistent)</h2>
        <p>Started (IST): <span id="start_time">loading...</span></p>
        <div id="value">--</div>
        <p>Next double in: <span id="countdown">--</span> seconds</p>
        <hr><h3>📋 Logs:</h3>
        <pre id="logs">loading...</pre>
        <script>
        async function updateData() {
            const res = await fetch('/api');
            const data = await res.json();
            document.getElementById('value').innerText = data.current_value;
            document.getElementById('countdown').innerText = data.next_double_in_seconds;
            document.getElementById('start_time').innerText = data.start_time_ist;
            document.getElementById('logs').innerText = data.recent_logs.join('\\n') || 'Waiting...';
        }
        updateData();
        setInterval(updateData, 2000);
        </script>
    </body></html>"""

@app.route("/api")
def api():
    value, start_time, logs = get_state()
    return jsonify({
        "current_value": value,
        "next_double_in_seconds": next_double_in["seconds"],
        "start_time_ist": start_time,
        "recent_logs": logs
    })

@app.route("/dbview")
def dbview():
    conn = get_db()
    cur = conn.cursor()

    sections = []

    # --- Counter tables ---
    cur.execute("SELECT * FROM counter_state")
    cols = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    sections.append(("counter_state", cols, rows))

    cur.execute("SELECT * FROM counter_logs ORDER BY id DESC LIMIT 15")
    cols = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    sections.append(("counter_logs", cols, rows))

    # --- Population tables ---
    cur.execute("SELECT * FROM population_state ORDER BY state_name")
    cols = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    sections.append(("population_state", cols, rows))

    cur.execute("SELECT * FROM population_history ORDER BY id DESC LIMIT 15")
    cols = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    sections.append(("population_history", cols, rows))

    # --- CPaaS tables ---
    cur.execute("SELECT * FROM cpaas_totals")
    cols = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    sections.append(("cpaas_totals", cols, rows))

    cur.execute("SELECT * FROM cpaas_minute_stats ORDER BY id DESC LIMIT 15")
    cols = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    sections.append(("cpaas_minute_stats", cols, rows))

    cur.close()
    conn.close()

    html = """
    <html>
    <head>
        <title>Database Viewer</title>
        <style>
            body { font-family:monospace; background:#111; color:#0f0; padding:30px; }
            h3 { color:cyan; margin-top:30px; }
            table { border-collapse:collapse; width:100%; margin-bottom:10px; }
            td, th { padding:6px 10px; text-align:left; border-bottom:1px solid #333; font-size:13px; }
            th { color:yellow; }
        </style>
    </head>
    <body>
        <h2>🗄️ Database Viewer (Read-Only)</h2>
        <p style="color:#aaa">Showing tables from shared-logs-db</p>
    """

    for table_name, cols, rows in sections:
        html += f"<h3>📋 {table_name} ({len(rows)} rows shown)</h3>"
        html += "<table><tr>" + "".join(f"<th>{c}</th>" for c in cols) + "</tr>"
        for row in rows:
            html += "<tr>" + "".join(f"<td>{val}</td>" for val in row) + "</tr>"
        html += "</table>"

    html += "</body></html>"
    return html
    
if __name__ == "__main__":
    init_db()
    threading.Thread(target=doubling_counter, daemon=True).start()
    app.run(host="0.0.0.0", port=10000, threaded=True)
