import json
from db.connection import get_db_connection

def validate_action(user_email: str, action: str):
    """Validates if an action is permissible for the user."""
    # Simple rule: Free users cannot downgrade (as they are already at bottom)
    # This is a placeholder for more complex business logic
    if action == "downgrade" and "free" in user_email: # simplistic check
         return json.dumps({"allowed": False, "reason": "Free users cannot downgrade"})
    return json.dumps({"allowed": True})

def hitl_confirmation(action: str, user_email: str):
    """Simulates a Human-In-The-Loop confirmation."""
    # In a real system, this might trigger a notification or wait for a signal.
    # For this mock, we'll auto-approve but log that HITL was requested.
    print(f"[HITL REQUEST] Action: {action} for {user_email} requires approval.")
    print(f"[HITL RESPONSE] Auto-approving for demo purposes.")
    return json.dumps({"approved": True, "approver": "System Admin"})
