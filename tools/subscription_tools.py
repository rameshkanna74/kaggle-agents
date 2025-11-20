import json
import datetime
from db.connection import get_db_connection

def get_user(email: str):
    """Retrieves user details by email."""
    with get_db_connection() as conn:
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user:
            return json.dumps(dict(user))
        return json.dumps({"error": "User not found"})

def cancel_subscription(email: str):
    """Cancels a user's subscription."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        user = cursor.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if not user:
            return json.dumps({"error": "User not found"})
        
        cursor.execute("UPDATE users SET active = 0, last_change = ? WHERE email = ?", 
                       (datetime.datetime.now().isoformat(), email))
        conn.commit()
        return json.dumps({"status": "success", "message": f"Subscription cancelled for {email}"})

def postpone_subscription(email: str, days: int):
    """Postpones the subscription renewal date."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        user = cursor.execute("SELECT renewal_date FROM users WHERE email = ?", (email,)).fetchone()
        if not user:
            return json.dumps({"error": "User not found"})
        
        current_renewal = datetime.date.fromisoformat(user['renewal_date']) if user['renewal_date'] else datetime.date.today()
        new_renewal = current_renewal + datetime.timedelta(days=days)
        
        cursor.execute("UPDATE users SET renewal_date = ?, last_change = ? WHERE email = ?", 
                       (new_renewal.isoformat(), datetime.datetime.now().isoformat(), email))
        conn.commit()
        return json.dumps({"status": "success", "new_renewal_date": new_renewal.isoformat()})

def upgrade_subscription(email: str, tier: str):
    """Upgrades the user's subscription tier."""
    if tier not in ['free', 'basic', 'pro']:
        return json.dumps({"error": "Invalid tier"})
        
    with get_db_connection() as conn:
        cursor = conn.cursor()
        user = cursor.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if not user:
            return json.dumps({"error": "User not found"})
            
        cursor.execute("UPDATE users SET subscription_tier = ?, last_change = ? WHERE email = ?", 
                       (tier, datetime.datetime.now().isoformat(), email))
        conn.commit()
        return json.dumps({"status": "success", "message": f"Upgraded to {tier}"})

def downgrade_subscription(email: str, tier: str):
    """Downgrades the user's subscription tier."""
    if tier not in ['free', 'basic', 'pro']:
        return json.dumps({"error": "Invalid tier"})
        
    with get_db_connection() as conn:
        cursor = conn.cursor()
        user = cursor.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if not user:
            return json.dumps({"error": "User not found"})
            
        cursor.execute("UPDATE users SET subscription_tier = ?, last_change = ? WHERE email = ?", 
                       (tier, datetime.datetime.now().isoformat(), email))
        conn.commit()
        return json.dumps({"status": "success", "message": f"Downgraded to {tier}"})
