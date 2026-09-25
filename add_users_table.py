import sqlite3


conn = sqlite3.connect("inventory.db")

conn.execute(
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """
)

conn.commit()
conn.close()

print("usersテーブルを確認しました")
