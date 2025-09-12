# server.py
from flask import Flask, request, jsonify
from libsql_client import create_client_sync
import os
import time

app = Flask(__name__)

# إعداد Turso DB عبر متغيرات البيئة
DATABASE_URL = os.getenv("DATABASE_URL")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")

client = create_client_sync(url=DATABASE_URL, auth_token=AUTH_TOKEN)

# إنشاء جدول log إذا لم يكن موجود
client.execute("""
CREATE TABLE IF NOT EXISTS users_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    ip TEXT,
    search TEXT,
    timestamp TEXT
)
""")

@app.route("/log_search", methods=["POST"])
def log_search():
    try:
        data = request.get_json() or {}
        username = data.get("username", "unknown")
        ip = data.get("ip", "0.0.0.0")
        search = data.get("search", "")
        timestamp = data.get("timestamp", str(int(time.time())))
        client.execute(
            "INSERT INTO users_log (username, ip, search, timestamp) VALUES (?, ?, ?, ?)",
            (username, ip, search, timestamp)
        )
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
