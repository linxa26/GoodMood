import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), 'moodpress.db')

conn = sqlite3.connect(DB_PATH)
rows = conn.execute("SELECT id, name, email, password FROM users").fetchall()
conn.close()

if not rows:
    print("❌ В таблице users пока нет данных.")
else:
    print("✅ Пользователи найдены:")
    for row in rows:
        print(row)
