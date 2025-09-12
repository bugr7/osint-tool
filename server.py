# server.py
from flask import Flask, request, jsonify
from libsql_client import create_client_sync
from migrate import migrate
import os

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")

client = create_client_sync(url=DATABASE_URL, auth_token=AUTH_TOKEN)
migrate(client)

@app.route("/log_search", methods=["POST"])
def log_search():
    data = request.get_json(force=True)
    try:
        client.execute(
            "INSERT INTO users_log (username, ip, os, search, created_at) VALUES (?, ?, ?, ?, ?)",
            (data.get("username", ""),
             data.get("ip", ""),
             data.get("os", ""),
             data.get("search", ""),
             data.get("created_at", ""))
        )
    except Exception as e:
        print("DB insert error:", e)
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
