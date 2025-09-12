# server.py
from flask import Flask, request, jsonify
from libsql_client import create_client_sync
from migrate import migrate
import os

app = Flask(__name__)

# ===== إعداد Turso =====
DATABASE_URL = os.getenv("DATABASE_URL")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")

client = create_client_sync(url=DATABASE_URL, auth_token=AUTH_TOKEN)
migrate(client)

# جدول logs
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

# ===== endpoint لتسجيل البحث =====
@app.route("/log", methods=["POST"])
def log_search():
    data = request.get_json() or {}
    try:
        client.execute(
            "INSERT INTO users_log (username, os, country, ip, search) VALUES (?, ?, ?, ?, ?)",
            (
                data.get("username", "Unknown"),
                data.get("os", "Unknown"),
                data.get("country", "Unknown"),
                data.get("ip", "0.0.0.0"),
                data.get("search", "")
            )
        )
    except Exception as e:
        print("DB Insert Error:", e)
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
