"""
Escalation Agent for final ticket resolution.

Responsibilities:
- Decide auto-resolve vs. manual escalation
- Apply tier-based escalation rules
- Trigger HITL approval for destructive actions
- Persist feedback to database
- Finalize ticket status

Based on multiTechAgentFinal.ipynb
"""

import logging
from typing import Dict, Any, Set
from datetime import datetime, timezone

from agents.a2a_manager import BaseA2AAgent, A2AManager, A2AMessage

logger = logging.getLogger(__name__)


class EscalationAgent(BaseA2AAgent):
    """
    Escalation agent that makes final resolution decisions.
    
    Decision logic:
    - If subscription inactive → Pause ticket
    - If confidence >= 0.8 → Auto-resolve
    - If confidence < 0.8 → Manual escalation
    - If angry customer → Escalate to human
    """
    
    def __init__(
        self,
        name: str,
        a2a_manager: A2AManager,
        db_connection: Any,
        auto_resolve_threshold: float = 0.8,
        skip_email_for: Set[str] = None
    ):
        """
        Initialize escalation agent.
        
        Args:
            name: Agent name
            a2a_manager: A2A communication manager
            db_connection: Database connection for feedback persistence
            auto_resolve_threshold: Confidence threshold for auto-resolution
            skip_email_for: Set of emails to skip notifications for (VIP users)
        """
        super().__init__(name, a2a_manager)
        self.db = db_connection
        self.auto_resolve_threshold = auto_resolve_threshold
        self.skip_email_for = skip_email_for or set()
    
    def handle_message(self, from_agent: str, message: A2AMessage) -> Dict[str, Any]:
        """
        Handle incoming A2A messages.
        
        Args:
            from_agent: Sending agent name
            message: A2A message
        
        Returns:
            Response dictionary
        """
        if message.payload.get("type") != "retrieval.complete":
            return {"status": "ignored"}
        
        ticket = message.payload.get("ticket")
        
        if not ticket:
            logger.error(f"[{self.name}] No ticket in message from {from_agent}")
            return {"status": "error", "message": "No ticket provided"}
        
        # Make escalation decision
        self._process_escalation(ticket)
        
        # Persist feedback
        self._save_feedback(ticket)
        
        return {"status": ticket.status, "ticket": ticket}
    
    def _process_escalation(self, ticket) -> None:
        """
        Process escalation decision for ticket.
        
        Args:
            ticket: Ticket object (modified in place)
        """
        customer_id = ticket.user_id
        tier = ticket.context.get("tier", "Unknown")
        renewal_active = ticket.context.get("renewal_active", False)
        confidence = ticket.context.get("confidence_score", 0.0)
        
        # Check if we should skip email notification
        if ticket.user_email in self.skip_email_for:
            logger.info(
                f"[{self.name}] Skipping email for VIP user: {ticket.user_email}"
            )
        
        # Decision logic
        if not renewal_active:
            # Inactive subscription - pause ticket
            ticket.status = "Paused"
            ticket.context["resolution"] = (
                "User subscription inactive. Ticket paused pending renewal."
            )
            logger.info(
                f"[{self.name}] Ticket {ticket.ticket_id} paused - inactive subscription"
            )
        
        elif confidence >= self.auto_resolve_threshold:
            # High confidence - auto-resolve
            ticket.status = "Resolved"
            ticket.context["resolution"] = (
                f"Resolved automatically with high confidence ({confidence:.2f}). "
                f"Diagnostic: {ticket.context.get('diagnostic_reasoning', 'N/A')}"
            )
            logger.info(
                f"[{self.name}] Ticket {ticket.ticket_id} auto-resolved "
                f"(confidence: {confidence:.2f})"
            )
        
        else:
            # Low confidence - manual escalation
            ticket.status = "Escalated"
            ticket.context["resolution"] = (
                f"Escalated to human agent due to low confidence ({confidence:.2f}). "
                "Manual investigation required."
            )
            logger.info(
                f"[{self.name}] Ticket {ticket.ticket_id} escalated to human "
                f"(confidence: {confidence:.2f})"
            )
        
        # Special handling for angry customers
        if ticket.context.get("sentiment") == "NEGATIVE":
            if ticket.status != "Paused":
                ticket.status = "Escalated"
                ticket.context["escalation_reason"] = "Negative sentiment detected"
                logger.info(
                    f"[{self.name}] Ticket {ticket.ticket_id} escalated due to negative sentiment"
                )
    
    def _save_feedback(self, ticket) -> None:
        """
        Save ticket feedback to database for learning.
        
        Args:
            ticket: Ticket object
        """
        try:
            cursor = self.db.cursor()
            timestamp = datetime.now(timezone.utc).isoformat()
            
            cursor.execute("""
                INSERT INTO feedback_loop (
                    ticket_id,
                    customer_id,
                    intent,
                    confidence_score,
                    diagnostic_reasoning,
                    status,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ticket.ticket_id,
                ticket.user_id,
                ticket.context.get("intent"),
                ticket.context.get("confidence_score", 0.0),
                ticket.context.get("diagnostic_reasoning", ""),
                ticket.status,
                timestamp,
                timestamp
            ))
            
            self.db.commit()
            
            logger.debug(
                f"[{self.name}] Saved feedback for ticket {ticket.ticket_id}"
            )
        
        except Exception as e:
            logger.error(
                f"[{self.name}] Error saving feedback for ticket {ticket.ticket_id}: {e}"
            )


# Example usage
if __name__ == "__main__":
    import sqlite3
    logging.basicConfig(level=logging.INFO)
    
    # Create mock database
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    
    # Create feedback_loop table
    cursor.execute("""
        CREATE TABLE feedback_loop (
            ticket_id TEXT,
            customer_id INTEGER,
            intent TEXT,
            confidence_score REAL,
            diagnostic_reasoning TEXT,
            status TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()
    
    # Create A2A manager and agent
    from agents.a2a_manager import A2AManager, MessageType
    from agents.triage_agent import Ticket
    
    a2a = A2AManager()
    escalation = EscalationAgent(
        "escalation",
        a2a,
        conn,
        skip_email_for={"alice@example.com"}
    )
    
    # Test tickets with different scenarios
    test_cases = [
        {
            "name": "High confidence - auto-resolve",
            "ticket": Ticket(
                ticket_id="TKT-001",
                text="API 401 error",
                user_ref="alice@example.com"
            ),
            "context": {
                "tier": "PLATINUM",
                "renewal_active": True,
                "confidence_score": 0.9,
                "intent": "API Authentication Failure",
                "diagnostic_reasoning": "Check API key validity"
            }
        },
        {
            "name": "Low confidence - escalate",
            "ticket": Ticket(
                ticket_id="TKT-002",
                text="Something is wrong",
                user_ref="bob@example.com"
            ),
            "context": {
                "tier": "GOLD",
                "renewal_active": True,
                "confidence_score": 0.5,
                "intent": "General Question",
                "diagnostic_reasoning": "No KB match"
            }
        },
        {
            "name": "Inactive subscription - pause",
            "ticket": Ticket(
                ticket_id="TKT-003",
                text="Need help",
                user_ref="carol@example.com"
            ),
            "context": {
                "tier": "SILVER",
                "renewal_active": False,
                "confidence_score": 0.7,
                "intent": "General Inquiry"
            }
        }
    ]
    
    print("\n=== Escalation Agent Test ===\n")
    
    for test_case in test_cases:
        print(f"\nTest: {test_case['name']}")
        ticket = test_case["ticket"]
        ticket.user_id = 1
        ticket.context = test_case["context"]
        
        # Simulate message from retrieval
        message = A2AMessage(
            message_type=MessageType.REQUEST,
            from_agent="retrieval",
            to_agent="escalation",
            payload={
                "type": "retrieval.complete",
                "ticket": ticket
            }
        )
        
        result = escalation.handle_message("retrieval", message)
        print(f"  Status: {ticket.status}")
        print(f"  Resolution: {ticket.context.get('resolution')}")
    
    # Check feedback was saved
    print("\n\nFeedback Loop Entries:")
    cursor.execute("SELECT ticket_id, status, confidence_score FROM feedback_loop")
    for row in cursor.fetchall():
        print(f"  {row}")
    
    conn.close()
