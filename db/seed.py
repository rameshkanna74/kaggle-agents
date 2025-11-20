import sys
import os
import datetime

# Add project root to path to allow imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from db.connection import init_db, get_db_connection

def seed_data():
    print("Initializing database...")
    init_db()
    
    print("Seeding data...")
    users = [
        ('Alice Free', 'free_user@example.com', 'free', None, 1, 0.0),
        ('Bob Basic', 'basic_user@example.com', 'basic', (datetime.date.today() + datetime.timedelta(days=30)).isoformat(), 1, 0.0),
        ('Charlie Pro', 'pro_user@example.com', 'pro', (datetime.date.today() + datetime.timedelta(days=30)).isoformat(), 1, 0.0)
    ]

    invoices = [
        (1, 0.0, '2023-10-01', 1), # Free user invoice (dummy)
        (1, 0.0, '2023-11-01', 1),
        (1, 0.0, '2023-12-01', 1),
        (2, 9.99, '2023-10-01', 1),
        (2, 9.99, '2023-11-01', 1),
        (2, 9.99, '2023-12-01', 0), # Unpaid
        (3, 29.99, '2023-10-01', 1),
        (3, 29.99, '2023-11-01', 1),
        (3, 29.99, '2023-12-01', 0) # Unpaid
    ]

    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if data exists to avoid duplicates if run multiple times
        cursor.execute("SELECT count(*) FROM users")
        if cursor.fetchone()[0] > 0:
            print("Database already contains data. Skipping seed.")
            return

        cursor.executemany(
            "INSERT INTO users (name, email, subscription_tier, renewal_date, active, balance) VALUES (?, ?, ?, ?, ?, ?)",
            users
        )
        
        cursor.executemany(
            "INSERT INTO invoices (user_id, amount, issued, paid) VALUES (?, ?, ?, ?)",
            invoices
        )
        
        conn.commit()
        print("Seeding complete.")

if __name__ == "__main__":
    seed_data()
