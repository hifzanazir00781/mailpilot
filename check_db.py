import sqlite3

conn = sqlite3.connect('data/app.db')
cur = conn.cursor()

# Tables list
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print("Tables in DB:")
for t in tables:
    print(f"  - {t}")

# chat_history columns
print("\nchat_history columns:")
cur.execute("PRAGMA table_info(chat_history)")
cols = [row[1] for row in cur.fetchall()]
print(f"  {cols}")

# chat_sessions columns (if exists)
if 'chat_sessions' in tables:
    print("\nchat_sessions columns:")
    cur.execute("PRAGMA table_info(chat_sessions)")
    cols2 = [row[1] for row in cur.fetchall()]
    print(f"  {cols2}")

# Count sessions
if 'chat_sessions' in tables:
    cur.execute("SELECT COUNT(*) FROM chat_sessions")
    print(f"\nTotal chat_sessions: {cur.fetchone()[0]}")

# Count history
cur.execute("SELECT COUNT(*) FROM chat_history")
print(f"Total chat_history rows: {cur.fetchone()[0]}")

conn.close()