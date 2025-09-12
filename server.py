# server.py
from flask import Flask, request, jsonify
from libsql_client import create_client_sync
from migrate import migrate
import os
import platform
import time

app = Flask(__name__)

# ===== إعداد Turso DB من متغيرات Railway =====
DATABASE_URL = os.getenv("DATABASE_URL")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")

client = create_client_sync(url=DATABASE_URL, auth_token=AUTH_TOKEN)
migrate(client)

# إنشاء جدول تسجيل البحث
client.execute("""
CREATE TABLE IF NOT EXISTS users_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    search TEXT,
    ip TEXT,
    os TEXT,
    timestamp TEXT
)
""")

@app.route("/log_search", methods=["POST"])
def log_search():
    data = request.get_json(silent=True) or {}
    search = data.get("search", "")
    ip = data.get("ip", "")
    os_name = data.get("os", "")
    timestamp = data.get("timestamp", "")
    if search:
        try:
            client.execute(
                "INSERT INTO users_log (search, ip, os, timestamp) VALUES (?, ?, ?, ?)",
                (search, ip, os_name, timestamp)
            )
        except Exception as e:
            print("DB insert error:", e)
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
