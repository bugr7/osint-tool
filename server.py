from flask import Flask, request, jsonify
from libsql_client import create_client_sync
from migrate import migrate
import os

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

# إنشاء جدول تسجيل البحث
if client:
    try:
        client.execute("""
        CREATE TABLE IF NOT EXISTS users_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            os TEXT,
            ip TEXT,
            search TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    except Exception as e:
        print("Error creating users_log:", e)


@app.route("/log_search", methods=["POST"])
def log_search():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data received"}), 400

        username = data.get("username", "unknown")
        os_name = data.get("os", "unknown")
        ip = data.get("ip", "0.0.0.0")
        search = data.get("search", "")

        if client:
            try:
                client.execute(
                    "INSERT INTO users_log (username, os, ip, search) VALUES (?, ?, ?, ?)",
                    (username, os_name, ip, search)
                )
            except Exception as e:
                print("DB insert error:", e)

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print("Error in /log_search:", e)
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
