import sqlite3
from werkzeug.security import generate_password_hash
db = sqlite3.connect("database.db")
cur = db.cursor()
new_hash = generate_password_hash("NewPassword123")
cur.execute(
    "UPDATE users SET password = ?, is_admin = 1 WHERE email = ?",
    (new_hash, "sonehuncho@gmail.com")
)
db.commit()
db.close()
print("Admin password reset and admin flag set.")