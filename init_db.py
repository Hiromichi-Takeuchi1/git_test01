import sqlite3

conn = sqlite3.connect("inventory.db")

conn.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    stock INTEGER NOT NULL DEFAULT 0,
    proper_stock INTEGER NOT NULL
)
""")

conn.execute("""
INSERT INTO products (name, stock, proper_stock)
VALUES ('コーヒー豆', 10, 15)
""")

conn.execute("""
INSERT INTO products (name, stock, proper_stock)
VALUES ('ミルク', 5, 8)
""")

conn.commit()

conn.close()

print("データベースを作成しました")
