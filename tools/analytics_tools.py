import json
from db.connection import get_db_connection

def compute_monthly_revenue():
    """Computes total revenue for the current month."""
    with get_db_connection() as conn:
        # Sum of all paid invoices
        result = conn.execute("SELECT SUM(amount) as total FROM invoices WHERE paid = 1").fetchone()
        total = result['total'] if result['total'] else 0.0
        return json.dumps({"monthly_revenue": total})

def compute_tier_distribution():
    """Computes the distribution of users across subscription tiers."""
    with get_db_connection() as conn:
        rows = conn.execute("SELECT subscription_tier, COUNT(*) as count FROM users GROUP BY subscription_tier").fetchall()
        dist = {row['subscription_tier']: row['count'] for row in rows}
        return json.dumps(dist)

def compute_cancellation_rate():
    """Computes the percentage of inactive users."""
    with get_db_connection() as conn:
        total = conn.execute("SELECT COUNT(*) as count FROM users").fetchone()['count']
        if total == 0:
            return json.dumps({"cancellation_rate": 0.0})
            
        inactive = conn.execute("SELECT COUNT(*) as count FROM users WHERE active = 0").fetchone()['count']
        rate = (inactive / total) * 100
        return json.dumps({"cancellation_rate": round(rate, 2)})
