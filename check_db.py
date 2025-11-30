import sqlite3
import os

DB_PATH = 'app.db'

def check_user(email):
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print(f"Checking for user: {email}")
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    
    if user:
        print(f"Found user: {user}")
    else:
        print("User not found")
        
    print("\nAll users:")
    cursor.execute("SELECT id, name, email FROM users")
    for row in cursor.fetchall():
        print(row)
        
    cursor.execute("SELECT count(*) FROM users")
    count = cursor.fetchone()[0]
    print(f"Total users: {count}")
    
    conn.close()

check_user('alice@example.com')
