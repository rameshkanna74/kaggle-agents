"""
Retrieval Agent for knowledge base matching and diagnostics.

Responsibilities:
- Match tickets against known issues database
- Provide diagnostic reasoning
- Boost confidence scores based on KB matches
- Forward enriched tickets to escalation agent

Based on multiTechAgentFinal.ipynb
"""

import logging
from typing import Dict, Any, Optional
from agents.a2a_manager import BaseA2AAgent, A2AManager, A2AMessage

logger = logging.getLogger(__name__)


class RetrievalAgent(BaseA2AAgent):
    """
    Retrieval agent that enriches tickets with knowledge base data.
    
    Workflow:
    1. Receive triaged ticket
    2. Search known_issues table for matches
    3. Add diagnostic reasoning
    4. Boost confidence if KB match found
    5. Forward to escalation agent
    """
    
    def __init__(
        self,
        name: str,
        a2a_manager: A2AManager,
        db_connection: Any
    ):
        """
        Initialize retrieval agent.
        
        Args:
            name: Agent name
            a2a_manager: A2A communication manager
            db_connection: Database connection for KB lookup
        """
        super().__init__(name, a2a_manager)
        self.db = db_connection
    
    def handle_message(self, from_agent: str, message: A2AMessage) -> Dict[str, Any]:
        """
        Handle incoming A2A messages.
        
        Args:
            from_agent: Sending agent name
            message: A2A message
        
        Returns:
            Response dictionary
        """
        if message.payload.get("type") == "triage.complete":
            ticket = message.payload.get("ticket")
            
            if not ticket:
                logger.error(f"[{self.name}] No ticket in message from {from_agent}")
                return {"status": "error", "message": "No ticket provided"}
            
            # Process the ticket
            result = self._process_ticket(ticket)
            
            # Forward to escalation
            payload = {
                "type": "retrieval.complete",
                "ticket": ticket
            }
            
            response = self.send_to("escalation", payload)
            
            return response
        
        return {"status": "ignored"}
    
    def _process_ticket(self, ticket) -> Dict[str, Any]:
        """
        Process ticket by matching against knowledge base.
        
        Args:
            ticket: Ticket object
        
        Returns:
            Processing result
        """
        # Get intent from ticket
        intent = ticket.context.get("intent", "")
        text = ticket.text.lower()
        
        # Try to find KB match
        kb_match = self._find_kb_match(intent, text)
        
        if kb_match:
            # KB match found
            ticket.context["kb_match"] = {
                "issue_key": kb_match[0],
                "title": kb_match[1],
                "category": kb_match[2],
                "fix": kb_match[3],
                "confidence_boost": kb_match[4]
            }
            
            ticket.context["diagnostic_reasoning"] = kb_match[3]
            
            # Boost confidence
            original_confidence = ticket.context.get("confidence_score", 0.5)
            boosted_confidence = min(
                1.0,
                original_confidence + kb_match[4]
            )
            ticket.context["confidence_score"] = boosted_confidence
            
            logger.info(
                f"[{self.name}] KB match found for ticket {ticket.ticket_id}: "
                f"{kb_match[0]} (confidence: {original_confidence:.2f} → {boosted_confidence:.2f})"
            )
        else:
            # No KB match
            ticket.context["kb_match"] = None
            ticket.context["diagnostic_reasoning"] = "No known issue match found. Manual investigation required."
            
            logger.info(
                f"[{self.name}] No KB match for ticket {ticket.ticket_id}"
            )
        
        return {"status": "processed"}
    
    def _find_kb_match(self, intent: str, text: str) -> Optional[tuple]:
        """
        Find matching known issue from database.
        
        Args:
            intent: Classified intent
            text: Ticket text (lowercase)
        
        Returns:
            Known issue tuple or None
        """
        try:
            cursor = self.db.cursor()
            
            # Try exact intent match first
            if "401" in text or "unauthorized" in text:
                cursor.execute("""
                    SELECT issue_key, title, category, fix, confidence_boost
                    FROM known_issues
                    WHERE issue_key = 'api-auth-401'
                """)
                result = cursor.fetchone()
                if result:
                    return result
            
            if "timeout" in text:
                cursor.execute("""
                    SELECT issue_key, title, category, fix, confidence_boost
                    FROM known_issues
                    WHERE issue_key = 'api-timeout'
                """)
                result = cursor.fetchone()
                if result:
                    return result
            
            if "latency" in text or "slow" in text:
                cursor.execute("""
                    SELECT issue_key, title, category, fix, confidence_boost
                    FROM known_issues
                    WHERE issue_key = 'latency-eu'
                """)
                result = cursor.fetchone()
                if result:
                    return result
            
            if "rate limit" in text:
                cursor.execute("""
                    SELECT issue_key, title, category, fix, confidence_boost
                    FROM known_issues
                    WHERE issue_key = 'api-rate-limit'
                """)
                result = cursor.fetchone()
                if result:
                    return result
            
            # Try category-based match
            cursor.execute("""
                SELECT issue_key, title, category, fix, confidence_boost
                FROM known_issues
                WHERE category LIKE ?
                LIMIT 1
            """, (f"%{intent}%",))
            
            return cursor.fetchone()
            
        except Exception as e:
            logger.error(f"[{self.name}] Error finding KB match: {e}")
            return None


# Example usage
if __name__ == "__main__":
    import sqlite3
    logging.basicConfig(level=logging.INFO)
    
    # Create mock database
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    
    # Create known_issues table
    cursor.execute("""
        CREATE TABLE known_issues (
            issue_key TEXT PRIMARY KEY,
            title TEXT,
            category TEXT,
            fix TEXT,
            confidence_boost REAL
        )
    """)
    
    # Seed known issues
    cursor.executemany("""
        INSERT INTO known_issues VALUES (?, ?, ?, ?, ?)
    """, [
        ("api-auth-401", "API 401 Unauthorized Error", "API Failure",
         "Check API key validity and scope. Ensure correct API permissions.", 0.8),
        ("api-timeout", "API Timeout Error", "API Failure",
         "Check server load and retry API call. Ensure network connectivity.", 0.7),
        ("latency-eu", "Latency in EU Region", "Performance Issue",
         "Check regional server status. Investigate network latency or high load.", 0.6),
    ])
    conn.commit()
    
    # Create A2A manager and agents
    from agents.a2a_manager import A2AManager
    from agents.triage_agent import Ticket
    
    a2a = A2AManager()
    
    # Mock escalation agent
    class MockEscalationAgent(BaseA2AAgent):
        def handle_message(self, from_agent: str, message: A2AMessage):
            logger.info(f"[escalation] Received ticket from {from_agent}")
            return {"status": "processed"}
    
    escalation = MockEscalationAgent("escalation", a2a)
    retrieval = RetrievalAgent("retrieval", a2a, conn)
    
    # Test ticket
    ticket = Ticket(
        ticket_id="TKT-001",
        text="Getting 401 errors on API calls",
        user_ref="test@example.com"
    )
    ticket.context = {
        "intent": "API Authentication Failure",
        "confidence_score": 0.6
    }
    
    print("\n=== Retrieval Agent Test ===\n")
    
    # Simulate message from triage
    message = A2AMessage(
        message_type=MessageType.REQUEST,
        from_agent="triage",
        to_agent="retrieval",
        payload={
            "type": "triage.complete",
            "ticket": ticket
        }
    )
    
    result = retrieval.handle_message("triage", message)
    print(f"Result: {result}")
    print(f"Ticket context: {ticket.context}")
    
    conn.close()
