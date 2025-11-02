# migrate.py
def migrate(client):

    required_columns = ["username", "os", "country", "ip", "search", "created_at"]

    try:

        res = client.execute("PRAGMA table_info(users_log)")
        rows = None
        if hasattr(res, "rows"):
            rows = res.rows
        else:
            try:
                rows = list(res)
            except Exception:
                rows = []

        existing_columns = [r[1] for r in rows] if rows else []
    except Exception:
        existing_columns = []

    if "username" not in existing_columns and "search" not in existing_columns:
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
        except Exception:
            pass


    for column in required_columns:
        if column not in existing_columns:
            try:
                if column == "created_at":
                    client.execute(
                        "ALTER TABLE users_log ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                    )
                else:
                    client.execute(f"ALTER TABLE users_log ADD COLUMN {column} TEXT")
            except Exception:
    
                pass

