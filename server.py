# server.py
from flask import Flask, request, jsonify
from libsql_client import create_client_sync
from migrate import migrate
import os
import time

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")

# ===== إعداد Turso =====
client = create_client_sync(url=DATABASE_URL, auth_token=AUTH_TOKEN)
migrate(client)

client.execute("""
CREATE TABLE IF NOT EXISTS users_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT,
    ip TEXT,
    os TEXT,
    timestamp INTEGER
)
""")

@app.route("/log_search", methods=["POST"])
def log_search():
    try:
        data = request.get_json() or {}
        query = data.get("query", "")
        ip = data.get("ip", "")
        os_name = data.get("os", "")
        timestamp = data.get("timestamp", int(time.time()))

        client.execute(
            "INSERT INTO users_log (query, ip, os, timestamp) VALUES (?, ?, ?, ?)",
            (query, ip, os_name, timestamp)
        )
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print("Error logging search:", e)
        return jsonify({"status": "error"}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
