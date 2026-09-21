import sqlite3

conn = sqlite3.connect("incoming.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    role TEXT
)
""")

cursor.execute(
    "SELECT id FROM users WHERE username = ?",
    ("admin",)
)

user = cursor.fetchone()

if user:
    cursor.execute(
        """
        UPDATE users
        SET password = ?, role = ?
        WHERE username = ?
        """,
        ("admin123", "Administrator", "admin")
    )
    print("Password admin berhasil direset.")
else:
    cursor.execute(
        """
        INSERT INTO users (username, password, role)
        VALUES (?, ?, ?)
        """,
        ("admin", "admin123", "Administrator")
    )
    print("Akun admin berhasil dibuat.")

conn.commit()
conn.close()

print("Username : admin")
print("Password : admin123")