import json
from db.connection import get_db_connection

def log_activity(user_email: str, agent_name: str, action: str, details: str):
    """Logs an agent's activity."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Get user_id if possible, else None
        user = cursor.execute("SELECT id FROM users WHERE email = ?", (user_email,)).fetchone()
        user_id = user['id'] if user else None
        
        cursor.execute("INSERT INTO activity_log (user_id, agent_name, action, details) VALUES (?, ?, ?, ?)",
                       (user_id, agent_name, action, details))
        conn.commit()
        return json.dumps({"status": "logged"})
