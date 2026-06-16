from flask import request

@app.route("/dbview")
def dbview():
    # --- Simple password check via URL parameter ---
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

    conn = get_db()
    cur = conn.cursor()

    sections = []

    cur.execute("SELECT * FROM counter_state")
    cols = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    sections.append(("counter_state", cols, rows))

    cur.execute("SELECT * FROM counter_logs ORDER BY id DESC LIMIT 15")
    cols = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    sections.append(("counter_logs", cols, rows))

    cur.execute("SELECT * FROM population_state ORDER BY state_name")
    cols = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    sections.append(("population_state", cols, rows))

    cur.execute("SELECT * FROM population_history ORDER BY id DESC LIMIT 15")
    cols = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    sections.append(("population_history", cols, rows))

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
