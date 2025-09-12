# server.py
from flask import Flask, request, jsonify
from libsql_client import create_client_sync
from migrate import migrate
import os
import time

app = Flask(__name__)

# ===== إعداد Turso عبر Railway Variables =====
DATABASE_URL = os.getenv("DATABASE_URL")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")

client = None
try:
    client = create_client_sync(url=DATABASE_URL, auth_token=AUTH_TOKEN)
    migrate(client)
except Exception as e:
    print("⚠️ Turso init failed:", e)

# إنشاء جدول users_log إذا لم يكن موجود
if client:
    try:
        client.execute("""
        CREATE TABLE IF NOT EXISTS users_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            os TEXT,
            country TEXT,
            ip TEXT,
            search TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    except Exception as e:
        print("Error creating users_log:", e)


@app.route("/log_search", methods=["POST"])
def log_search():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "unknown")
    os_info = data.get("os", "unknown")
    country = data.get("country", "Unknown")
    ip = data.get("ip", "0.0.0.0")
    search_text = data.get("search", "")

    if client:
        try:
            client.execute(
                "INSERT INTO users_log (username, os, country, ip, search) VALUES (?, ?, ?, ?, ?)",
                (username, os_info, country, ip, search_text)
            )
        except Exception as e:
            print("⚠️ Failed to insert log:", e)

    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
