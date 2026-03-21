import sqlite3
conn = sqlite3.connect("C:/desktop/E-com site/store.db")
cursor = conn.cursor()
cursor.execute("UPDATE users SET is_admin = 1 WHERE email = 'sonehuncho@gmail.com'")
conn.commit()
cursor.execute("SELECT id, username, email, is_admin FROM users")
rows = cursor.fetchall()
for row in rows:
    print(row)
conn.close()
