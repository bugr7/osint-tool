from flask import Flask, request, jsonify
from libsql_client import create_client_sync
from migrate import migrate
import os

app = Flask(__name__)

# ===== إعداد Turso =====
DATABASE_URL = os.getenv("DATABASE_URL")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")

client = None
try:
    client = create_client_sync(url=DATABASE_URL, auth_token=AUTH_TOKEN)
    migrate(client)
except Exception as e:
    print("⚠️ Turso init failed:", e)

# إنشاء الجداول
if client:
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

@app.route("/log_search", methods=["POST"])
def log_search():
    data = request.get_json() or {}
    if client:
        try:
            client.execute(
                "INSERT INTO users_log (username, os, country, ip, search) VALUES (?, ?, ?, ?, ?)",
                (
                    data.get("username", "unknown"),
                    data.get("os", "unknown"),
                    data.get("country", "unknown"),
                    data.get("ip", "0.0.0.0"),
                    data.get("search", ""),
                ),
            )
        except Exception as e:
            print("DB insert error:", e)
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
