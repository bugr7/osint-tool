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

# إنشاء جدول إذا ماكانش
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

@app.route("/search", methods=["POST"])
def search():
    data = request.json
    identifier = data.get("identifier", "")
    if not identifier:
        return jsonify([])

    # تخزين البحث
    client.execute(
        "INSERT INTO users_log (username, os, country, ip, search) VALUES (?, ?, ?, ?, ?)",
        ("server_user", "ServerOS", "Unknown", "0.0.0.0", identifier)
    )

    # مثال للبيانات المرجعة
    results = [{"platform": "Facebook", "link": f"https://facebook.com/{identifier}"}]
    return jsonify(results)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
