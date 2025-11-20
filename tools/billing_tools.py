import json
import datetime
from db.connection import get_db_connection

def generate_invoice(email: str, amount: float):
    """Generates a new invoice for a user."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        user = cursor.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if not user:
            return json.dumps({"error": "User not found"})
            
        cursor.execute("INSERT INTO invoices (user_id, amount, issued, paid) VALUES (?, ?, ?, 0)",
                       (user['id'], amount, datetime.date.today().isoformat()))
        conn.commit()
        return json.dumps({"status": "success", "message": "Invoice generated"})

def get_unpaid_invoices(email: str):
    """Retrieves all unpaid invoices for a user."""
    with get_db_connection() as conn:
        user = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if not user:
            return json.dumps({"error": "User not found"})
            
        invoices = conn.execute("SELECT * FROM invoices WHERE user_id = ? AND paid = 0", (user['id'],)).fetchall()
        return json.dumps([dict(inv) for inv in invoices])

def mark_invoice_paid(invoice_id: int):
    """Marks an invoice as paid."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE invoices SET paid = 1 WHERE id = ?", (invoice_id,))
        if cursor.rowcount == 0:
             return json.dumps({"error": "Invoice not found"})
        conn.commit()
        return json.dumps({"status": "success", "message": "Invoice marked as paid"})
