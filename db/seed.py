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
    
    # Enhanced users with new tier system
    users = [
        ('Alice Platinum', 'alice@example.com', 'platinum', (datetime.date.today() + datetime.timedelta(days=365)).isoformat(), 1, 100.0),
        ('Bob Gold', 'bob@example.com', 'gold', (datetime.date.today() + datetime.timedelta(days=180)).isoformat(), 1, 50.0),
        ('Carol Silver', 'carol@example.com', 'silver', (datetime.date.today() - datetime.timedelta(days=30)).isoformat(), 0, 0.0),
        ('Dave Standard', 'dave@example.com', 'standard', (datetime.date.today() + datetime.timedelta(days=90)).isoformat(), 1, 25.0),
        ('Eve Free', 'eve@example.com', 'free', None, 1, 0.0),
        # Legacy users for backward compatibility
        ('Frank Basic', 'basic_user@example.com', 'basic', (datetime.date.today() + datetime.timedelta(days=30)).isoformat(), 1, 10.0),
        ('Grace Pro', 'pro_user@example.com', 'pro', (datetime.date.today() + datetime.timedelta(days=30)).isoformat(), 1, 30.0)
    ]

    invoices = [
        (1, 99.99, '2024-01-01', 1),  # Platinum
        (1, 99.99, '2024-02-01', 1),
        (1, 99.99, '2024-03-01', 0),  # Unpaid
        (2, 49.99, '2024-01-01', 1),  # Gold
        (2, 49.99, '2024-02-01', 1),
        (2, 49.99, '2024-03-01', 0),  # Unpaid
        (3, 19.99, '2024-01-01', 1),  # Silver
        (3, 19.99, '2024-02-01', 0),  # Unpaid
        (4, 9.99, '2024-01-01', 1),   # Standard
        (4, 9.99, '2024-02-01', 0),   # Unpaid
    ]
    
    # Known issues for KB matching
    known_issues = [
        ('api-auth-401', 'API 401 Unauthorized Error', 'API Failure',
         'Check API key validity and scope. Ensure correct API permissions. Regenerate key if needed.', 0.8, 1),
        ('api-timeout', 'API Timeout Error', 'API Failure',
         'Check server load and retry API call. Ensure network connectivity. Consider increasing timeout.', 0.7, 2),
        ('latency-eu', 'Latency in EU Region', 'Performance Issue',
         'Check regional server status. Investigate network latency or high load. Consider CDN.', 0.6, 2),
        ('connection-error', 'Connection Error', 'Network Issue',
         'Verify internet connectivity. Check endpoint reachability. Review firewall settings.', 0.7, None),
        ('api-rate-limit', 'API Rate Limit Exceeded', 'API Failure',
         'Increase rate limit or reduce request frequency. Check quotas. Upgrade tier if needed.', 0.9, None),
        ('billing-failed', 'Payment Processing Failed', 'Billing Issue',
         'Verify payment method. Check card expiration. Contact bank if issue persists.', 0.85, None),
        ('subscription-downgrade', 'Subscription Downgrade Request', 'Subscription',
         'Process downgrade at next billing cycle. Notify user of feature changes.', 0.9, None),
    ]

    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if data exists to avoid duplicates if run multiple times
        cursor.execute("SELECT count(*) FROM users")
        if cursor.fetchone()[0] > 0:
            print("Database already contains data. Skipping seed.")
            return

        # Insert users
        cursor.executemany(
            "INSERT INTO users (name, email, subscription_tier, renewal_date, active, balance) VALUES (?, ?, ?, ?, ?, ?)",
            users
        )
        
        # Insert invoices
        cursor.executemany(
            "INSERT INTO invoices (user_id, amount, issued, paid) VALUES (?, ?, ?, ?)",
            invoices
        )
        
        # Insert known issues
        cursor.executemany(
            "INSERT INTO known_issues (issue_key, title, category, fix, confidence_boost, customer_id) VALUES (?, ?, ?, ?, ?, ?)",
            known_issues
        )
        
        # Insert some sample analytics
        analytics = [
            ('total_users', len(users)),
            ('active_users', sum(1 for u in users if u[4] == 1)),
            ('monthly_revenue', sum(i[1] for i in invoices if i[3] == 1)),
            ('cancellation_rate', 0.05),
        ]
        
        cursor.executemany(
            "INSERT INTO analytics (metric, value) VALUES (?, ?)",
            analytics
        )
        
        conn.commit()
        print(f"Seeding complete:")
        print(f"  - {len(users)} users")
        print(f"  - {len(invoices)} invoices")
        print(f"  - {len(known_issues)} known issues")
        print(f"  - {len(analytics)} analytics metrics")

if __name__ == "__main__":
    seed_data()

