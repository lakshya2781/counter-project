from flask import Flask, jsonify, request
import threading, time, datetime, os
from datetime import timezone, timedelta
import psycopg2

app = Flask(__name__)

IST = timezone(timedelta(hours=5, minutes=30))
def now_ist():
    return datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

DATABASE_URL = os.environ.get("DATABASE_URL")
DBVIEW_PASSWORD = os.environ.get("DBVIEW_PASSWORD", "Lakshya2781")

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

next_double_in = {"seconds": 1800}

def reset_counter():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE counter_state SET value=1, start_time=%s WHERE id=1", (now_ist(),))
    cur.execute("DELETE FROM counter_logs")  # clear old logs too
    conn.commit()
    cur.close()
    conn.close()
    
def doubling_counter():
    while True:
        for remaining in range(1800, 0, -1):
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
        #value{font-size:4em;color:lime;} #countdown{color:yellow;} pre{color:#0ff;}
        #resetBtn{background:#900;color:white;border:none;padding:10px 20px;
        font-family:monospace;font-size:14px;cursor:pointer;margin-top:15px;border-radius:4px;}
        #resetBtn:hover{background:#c00;}</style>
    </head>
    <body>
        <h2>🖥️ Cloud Counter Monitor (Persistent)</h2>
        <p>Started (IST): <span id="start_time">loading...</span></p>
        <div id="value">--</div>
        <p>Next double in: <span id="countdown">--</span> seconds</p>
        <button id="resetBtn" onclick="resetCounter()">🔄 Reset Counter</button>
        <hr><h3>📋 Logs:</h3>
        <pre id="logs">loading...</pre>
        <p><a href="/dbview" style="color:cyan">🗄️ View Database</a></p>
        <script>
        async function updateData() {
            const res = await fetch('/api');
            const data = await res.json();
            document.getElementById('value').innerText = data.current_value;
            document.getElementById('countdown').innerText = data.next_double_in_seconds;
            document.getElementById('start_time').innerText = data.start_time_ist;
            document.getElementById('logs').innerText = data.recent_logs.join('\\n') || 'Waiting...';
        }
        async function resetCounter() {
            if (!confirm('Are you sure you want to reset the counter to 1?')) return;
            const res = await fetch('/reset', { method: 'POST' });
            const result = await res.json();
            alert(result.message);
            updateData();
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

@app.route("/reset", methods=["POST"])
def reset():
    reset_counter()
    next_double_in["seconds"] = 1800  # restart the 30-min cycle too
    return jsonify({"status": "reset", "message": "Counter reset to 1"})
    
@app.route("/dbview")
def dbview():
    provided_password = request.args.get("password", "")
    if provided_password != DBVIEW_PASSWORD:
        return """
        <html>
        <head><title>Locked</title></head>
        <body style="font-family:monospace; background:#111; color:#0f0; padding:60px; text-align:center;">
            <h2>🔒 Access Restricted</h2>
            <p>Add ?password=YOUR_PASSWORD to the URL to view this page.</p>
        </body></html>
        """, 401

    # --- Read filter parameters from URL ---
    search_text = request.args.get("search", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    table_filter = request.args.get("table", "all")
    row_limit_raw = request.args.get("limit", "200").strip()

    # Validate row limit
    if row_limit_raw == "all":
        row_limit = None
    else:
        try:
            row_limit = int(row_limit_raw)
            if row_limit <= 0:
                row_limit = 200
        except ValueError:
            row_limit = 200

    conn = get_db()
    cur = conn.cursor()
    sections = []

    table_list = ["counter_state", "counter_logs", "population_state",
                  "population_history", "cpaas_totals", "cpaas_minute_stats",
                  "stock_state", "stock_history"]

    for table_name in table_list:
        if table_filter != "all" and table_filter != table_name:
            continue

        has_log_time = table_name in ("counter_logs", "population_history",
                                       "cpaas_minute_stats", "stock_history")

        if has_log_time:
            query = f"SELECT * FROM {table_name} WHERE 1=1"
            params = []
            if date_from:
                query += " AND log_time >= %s"
                params.append(date_from)
            if date_to:
                query += " AND log_time <= %s"
                params.append(date_to + " 23:59:59")
            if search_text:
                query += " AND log_time::text ILIKE %s"
                params.append(f"%{search_text}%")
            query += " ORDER BY id DESC"
            if row_limit is not None:
                query += " LIMIT %s"
                params.append(row_limit)
            cur.execute(query, params)
        else:
            cur.execute(f"SELECT * FROM {table_name} ORDER BY 1")

        cols = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        sections.append((table_name, cols, rows))

    cur.close()
    conn.close()

    # --- Build filter form ---
    table_options = "".join(
        f'<option value="{t}" {"selected" if table_filter==t else ""}>{t}</option>'
        for t in table_list
    )

    limit_options_list = ["20", "50", "200", "500", "1000", "all"]
    limit_options = "".join(
        f'<option value="{l}" {"selected" if row_limit_raw==l else ""}>{"All" if l=="all" else l}</option>'
        for l in limit_options_list
    )

    filter_html = f"""
    <form method="GET" style="margin-bottom:25px; background:#1a1a1a; padding:15px; border-radius:6px;">
        <input type="hidden" name="password" value="{provided_password}">
        <label>Table:
            <select name="table">
                <option value="all" {"selected" if table_filter=="all" else ""}>All Tables</option>
                {table_options}
            </select>
        </label>
        &nbsp;&nbsp;
        <label>Show:
            <select name="limit">{limit_options}</select> rows
        </label>
        &nbsp;&nbsp;
        <label>Search (timestamp text): <input type="text" name="search" value="{search_text}" placeholder="e.g. 2026-06-17"></label>
        &nbsp;&nbsp;
        <label>From: <input type="date" name="date_from" value="{date_from}"></label>
        &nbsp;&nbsp;
        <label>To: <input type="date" name="date_to" value="{date_to}"></label>
        &nbsp;&nbsp;
        <button type="submit" style="background:#0a5;color:white;border:none;padding:6px 14px;cursor:pointer;border-radius:4px;">Apply Filters</button>
        <a href="/dbview?password={provided_password}" style="color:cyan; margin-left:10px;">Clear Filters</a>
    </form>
    """

    html = f"""
    <html>
    <head>
        <title>Database Viewer</title>
        <style>
            body {{ font-family:monospace; background:#111; color:#0f0; padding:30px; }}
            h3 {{ color:cyan; margin-top:30px; }}
            table {{ border-collapse:collapse; width:100%; margin-bottom:10px; }}
            td, th {{ padding:6px 10px; text-align:left; border-bottom:1px solid #333; font-size:13px; }}
            th {{ color:yellow; }}
            input, select {{ background:#222; color:#0f0; border:1px solid #444; padding:4px; }}
            label {{ color:#aaa; }}
        </style>
    </head>
    <body>
        <h2>🗄️ Database Viewer (Read-Only)</h2>
        <p style="color:#aaa">Showing tables from shared-logs-db</p>
        {filter_html}
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
