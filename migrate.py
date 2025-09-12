# migrate.py
def migrate(client):
    """
    يتأكد من وجود الأعمدة المطلوبة في جدول users_log.
    إذا ماكانوش موجودين يضيفهم.
    """
    required_columns = ["username", "os", "ip", "search", "created_at"]

    # جلب الأعمدة الحالية
    result = client.execute("PRAGMA table_info(users_log)").rows
    existing_columns = [row[1] for row in result]  # row[1] = اسم العمود

    # إنشاء الجدول إذا لم يكن موجود
    if not existing_columns:
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
        return

    # إضافة الأعمدة الناقصة
    for column in required_columns:
        if column not in existing_columns:
            if column == "created_at":
                client.execute(
                    "ALTER TABLE users_log ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                )
            else:
                client.execute(f"ALTER TABLE users_log ADD COLUMN {column} TEXT")
