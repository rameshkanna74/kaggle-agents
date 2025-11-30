"""
Triage Agent for customer support system.

Responsibilities:
- Resolve user by name OR email
- Classify intent hierarchically (broad category → specific intent)
- Assign priority (P1-P4) based on intent and user tier
- Calculate confidence scores
- Forward to retrieval agent via A2A

Based on multiTechAgentFinal.ipynb and customer-support-agent.ipynb
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from agents.a2a_manager import BaseA2AAgent, A2AManager, A2AMessage, MessageType
from safety.input_validator import InputValidator

logger = logging.getLogger(__name__)


class Priority(Enum):
    """Priority levels for tickets."""
    P1 = "P1"  # Critical - immediate attention
    P2 = "P2"  # High - same day
    P3 = "P3"  # Medium - within 3 days
    P4 = "P4"  # Low - within week


@dataclass
class Ticket:
    """
    Represents a customer support ticket.
    
    Flows through: Triage → Retrieval → Escalation
    """
    ticket_id: str
    text: str
    user_ref: str  # Can be name OR email
    
    # Resolved user info (filled by triage)
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    
    # Classification (filled by triage)
    context: Dict[str, Any] = None
    status: str = "New"
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}


class TriageAgent(BaseA2AAgent):
    """
    Triage agent that processes incoming tickets.
    
    Workflow:
    1. Validate input
    2. Resolve user (by name OR email)
    3. Classify intent hierarchically
    4. Assign priority and confidence
    5. Forward to retrieval agent
    """
    
    # Broad categories for hierarchical classification
    BROAD_CATEGORIES = [
        "Technical Support",
        "Billing & Subscription",
        "General Inquiry",
        "Complaint"
    ]
    
    # Specific intents per category
    INTENT_MAP = {
        "Technical Support": [
            "API Authentication Failure",
            "API Timeout",
            "Performance Issue",
            "Connection Error",
            "Bug Report"
        ],
        "Billing & Subscription": [
            "Subscription Cancellation",
            "Subscription Upgrade",
            "Subscription Downgrade",
            "Payment Issue",
            "Invoice Request"
        ],
        "Complaint": [
            "Service Dissatisfaction",
            "Escalation Request",
            "Refund Request",
            "Negative Feedback"
        ],
        "General Inquiry": [
            "Policy Question",
            "FAQ",
            "Feature Request",
            "General Question"
        ]
    }
    
    def __init__(
        self,
        name: str,
        a2a_manager: A2AManager,
        db_connection: Any
    ):
        """
        Initialize triage agent.
        
        Args:
            name: Agent name
            a2a_manager: A2A communication manager
            db_connection: Database connection for user lookup
        """
        super().__init__(name, a2a_manager)
        self.db = db_connection
        self.input_validator = InputValidator()
    
    def handle_message(self, from_agent: str, message: A2AMessage) -> Dict[str, Any]:
        """
        Handle incoming A2A messages.
        
        Args:
            from_agent: Sending agent name
            message: A2A message
        
        Returns:
            Response dictionary
        """
        logger.info(
            f"[{self.name}] Received {message.message_type.value} from {from_agent}"
        )
        
        # For now, just acknowledge
        return {"status": "ok"}
    
    def process_ticket(self, ticket: Ticket) -> Dict[str, Any]:
        """
        Process a ticket through triage.
        
        Args:
            ticket: Ticket to process
        
        Returns:
            Result dictionary with processed ticket
        """
        # Step 1: Validate input
        validation_result = self.input_validator.validate(ticket.text)
        
        if not validation_result.is_valid:
            ticket.status = "Rejected"
            ticket.context["rejection_reason"] = "Input validation failed"
            ticket.context["validation_issues"] = [
                issue.message for issue in validation_result.issues
            ]
            return {"status": "rejected", "ticket": ticket}
        
        # Use sanitized input
        ticket.text = validation_result.sanitized_input
        ticket.context["risk_score"] = validation_result.risk_score
        
        # Step 2: Resolve user
        user = self._resolve_user(ticket.user_ref)
        
        if not user:
            ticket.status = "Escalated"
            ticket.context["resolution"] = "Unknown user"
            logger.warning(f"[{self.name}] Unknown user: {ticket.user_ref}")
            return {"status": "escalated", "ticket": ticket}
        
        # Set canonical user fields
        ticket.user_id = user[0]
        ticket.user_name = user[1]
        ticket.user_email = user[2]
        ticket.context["tier"] = user[3]
        ticket.context["renewal_active"] = bool(user[4])
        
        # Step 3: Classify intent
        category, intent, confidence = self._classify_intent(ticket.text)
        
        ticket.context.update({
            "category": category,
            "intent": intent,
            "confidence_score": confidence
        })
        
        # Step 4: Assign priority
        priority = self._assign_priority(intent, ticket.context["tier"], confidence)
        ticket.context["priority"] = priority.value
        
        logger.info(
            f"[{self.name}] Triaged ticket {ticket.ticket_id}: "
            f"{intent} (P{priority.value[1]}, confidence={confidence:.2f})"
        )
        
        # Step 5: Forward to retrieval agent
        payload = {
            "type": "triage.complete",
            "ticket": ticket
        }
        
        response = self.send_to("retrieval", payload)
        
        return response
    
    def _resolve_user(self, user_ref: str) -> Optional[tuple]:
        """
        Resolve user by name OR email.
        
        Args:
            user_ref: User name or email
        
        Returns:
            User tuple (id, name, email, tier, active) or None
        """
        try:
            cursor = self.db.cursor()
            
            # Try to resolve by email or name
            logger.info(f"[{self.name}] Resolving user: {user_ref}")
            cursor.execute("""
                SELECT id, name, email, subscription_tier, active
                FROM users
                WHERE LOWER(email) = LOWER(?) OR LOWER(name) = LOWER(?)
            """, (user_ref, user_ref))
            
            result = cursor.fetchone()
            logger.info(f"[{self.name}] Resolution result: {result}")
            return result
        except Exception as e:
            logger.error(f"[{self.name}] Error resolving user: {e}")
            return None
    
    def _classify_intent(self, text: str) -> tuple[str, str, float]:
        """
        Hierarchical intent classification.
        
        First classifies into broad category, then specific intent.
        
        Args:
            text: Ticket text
        
        Returns:
            Tuple of (category, specific_intent, confidence)
        """
        text_lower = text.lower()
        
        # Simple keyword-based classification (in production, use LLM)
        # Technical Support patterns
        if any(kw in text_lower for kw in ["401", "unauthorized", "auth", "api key"]):
            return "Technical Support", "API Authentication Failure", 0.9
        
        if any(kw in text_lower for kw in ["timeout", "slow", "latency", "performance"]):
            return "Technical Support", "Performance Issue", 0.85
        
        if any(kw in text_lower for kw in ["error", "bug", "broken", "not working"]):
            return "Technical Support", "Bug Report", 0.8
        
        # Billing & Subscription patterns
        if any(kw in text_lower for kw in ["cancel", "cancellation", "stop subscription"]):
            return "Billing & Subscription", "Subscription Cancellation", 0.95
        
        if any(kw in text_lower for kw in ["upgrade", "premium", "platinum"]):
            return "Billing & Subscription", "Subscription Upgrade", 0.9
        
        if any(kw in text_lower for kw in ["invoice", "bill", "payment", "charge"]):
            return "Billing & Subscription", "Invoice Request", 0.85
        
        # Complaint patterns
        if any(kw in text_lower for kw in ["angry", "terrible", "worst", "hate", "complaint"]):
            return "Complaint", "Service Dissatisfaction", 0.9
        
        if any(kw in text_lower for kw in ["refund", "money back"]):
            return "Complaint", "Refund Request", 0.95
        
        # Policy/FAQ patterns
        if any(kw in text_lower for kw in ["policy", "how to", "what is", "can i"]):
            return "General Inquiry", "Policy Question", 0.75
        
        # Default to general inquiry
        return "General Inquiry", "General Question", 0.6
    
    def _assign_priority(self, intent: str, tier: str, confidence: float) -> Priority:
        """
        Assign priority based on intent, user tier, and confidence.
        
        Args:
            intent: Specific intent
            tier: User subscription tier
            confidence: Classification confidence
        
        Returns:
            Priority level
        """
        # Critical intents
        if intent in ["API Authentication Failure", "Service Dissatisfaction"]:
            return Priority.P1
        
        # High priority for premium users
        if tier.upper() in ["PLATINUM", "GOLD"]:
            if intent in ["Subscription Cancellation", "Refund Request"]:
                return Priority.P1
            return Priority.P2
        
        # Medium priority
        if intent in ["Performance Issue", "Bug Report", "Payment Issue"]:
            return Priority.P2
        
        # Low confidence gets higher priority for review
        if confidence < 0.7:
            return Priority.P3
        
        # Default
        return Priority.P4


# Example usage
if __name__ == "__main__":
    import sqlite3
    logging.basicConfig(level=logging.INFO)
    
    # Create mock database
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            subscription_tier TEXT,
            active INTEGER
        )
    """)
    cursor.execute("""
        INSERT INTO users VALUES
        (1, 'Alice', 'alice@example.com', 'PLATINUM', 1),
        (2, 'Bob', 'bob@example.com', 'GOLD', 1)
    """)
    conn.commit()
    
    # Create A2A manager and agents
    a2a = A2AManager()
    
    # Mock retrieval agent
    class MockRetrievalAgent(BaseA2AAgent):
        def handle_message(self, from_agent: str, message: A2AMessage):
            logger.info(f"[retrieval] Received ticket from {from_agent}")
            return {"status": "processed"}
    
    retrieval = MockRetrievalAgent("retrieval", a2a)
    triage = TriageAgent("triage", a2a, conn)
    
    # Test ticket
    ticket = Ticket(
        ticket_id="TKT-001",
        text="My API key is giving 401 errors",
        user_ref="alice@example.com"
    )
    
    print("\n=== Triage Agent Test ===\n")
    result = triage.process_ticket(ticket)
    print(f"Result: {result}")
    print(f"Ticket context: {ticket.context}")
    
    conn.close()
