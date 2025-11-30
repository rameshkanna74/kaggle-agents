"""
Tests for A2A communication and agent workflows.

Tests:
- A2A manager functionality
- Triage agent classification
- Retrieval agent KB matching
- Escalation agent decision logic
- End-to-end workflow
"""

import pytest
import sqlite3
from agents.a2a_manager import A2AManager, BaseA2AAgent, MessageType, A2AMessage
from agents.triage_agent import TriageAgent, Ticket, Priority
from agents.retrieval_agent import RetrievalAgent
from agents.escalation_agent import EscalationAgent


@pytest.fixture
def db_connection():
    """Create in-memory database for testing."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    
    # Create tables
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
        CREATE TABLE known_issues (
            issue_key TEXT PRIMARY KEY,
            title TEXT,
            category TEXT,
            fix TEXT,
            confidence_boost REAL
        )
    """)
    
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
    
    # Insert test data
    cursor.execute("""
        INSERT INTO users VALUES
        (1, 'Alice', 'alice@example.com', 'PLATINUM', 1),
        (2, 'Bob', 'bob@example.com', 'GOLD', 1),
        (3, 'Carol', 'carol@example.com', 'SILVER', 0)
    """)
    
    cursor.execute("""
        INSERT INTO known_issues VALUES
        ('api-auth-401', 'API 401 Error', 'API Failure', 'Check API key', 0.8),
        ('api-timeout', 'API Timeout', 'API Failure', 'Retry request', 0.7)
    """)
    
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def a2a_manager():
    """Create A2A manager for testing."""
    return A2AManager()


class TestA2AManager:
    """Tests for A2A manager."""
    
    def test_agent_registration(self, a2a_manager):
        """Test agent registration."""
        class TestAgent(BaseA2AAgent):
            def handle_message(self, from_agent, message):
                return {"status": "ok"}
        
        agent = TestAgent("test_agent", a2a_manager)
        
        assert a2a_manager.is_registered("test_agent")
        assert "test_agent" in a2a_manager.list_agents()
    
    def test_duplicate_registration_fails(self, a2a_manager):
        """Test that duplicate registration raises error."""
        class TestAgent(BaseA2AAgent):
            def handle_message(self, from_agent, message):
                return {"status": "ok"}
        
        agent1 = TestAgent("test_agent", a2a_manager)
        
        with pytest.raises(ValueError):
            agent2 = TestAgent("test_agent", a2a_manager)
    
    def test_message_sending(self, a2a_manager):
        """Test sending messages between agents."""
        class EchoAgent(BaseA2AAgent):
            def handle_message(self, from_agent, message):
                return {"echo": message.payload.get("data")}
        
        agent1 = EchoAgent("agent1", a2a_manager)
        agent2 = EchoAgent("agent2", a2a_manager)
        
        response = agent1.send_to("agent2", {"data": "test"})
        
        assert response["echo"] == "test"
    
    def test_broadcast(self, a2a_manager):
        """Test broadcasting to all agents."""
        class CounterAgent(BaseA2AAgent):
            def __init__(self, name, a2a):
                super().__init__(name, a2a)
                self.count = 0
            
            def handle_message(self, from_agent, message):
                self.count += 1
                return {"count": self.count}
        
        agent1 = CounterAgent("agent1", a2a_manager)
        agent2 = CounterAgent("agent2", a2a_manager)
        agent3 = CounterAgent("agent3", a2a_manager)
        
        responses = a2a_manager.broadcast("agent1", {"test": "data"})
        
        assert len(responses) == 2  # Excludes sender
        assert agent2.count == 1
        assert agent3.count == 1


class TestTriageAgent:
    """Tests for triage agent."""
    
    def test_user_resolution(self, a2a_manager, db_connection):
        """Test user resolution by email."""
        # Create mock retrieval agent
        class MockRetrievalAgent(BaseA2AAgent):
            def handle_message(self, from_agent, message):
                return {"status": "ok"}
        
        retrieval = MockRetrievalAgent("retrieval", a2a_manager)
        triage = TriageAgent("triage", a2a_manager, db_connection)
        
        ticket = Ticket(
            ticket_id="TKT-001",
            text="I have an API issue",
            user_ref="alice@example.com"
        )
        
        result = triage.process_ticket(ticket)
        
        assert ticket.user_id == 1
        assert ticket.user_name == "Alice"
        assert ticket.user_email == "alice@example.com"
    
    def test_intent_classification(self, a2a_manager, db_connection):
        """Test intent classification."""
        class MockRetrievalAgent(BaseA2AAgent):
            def handle_message(self, from_agent, message):
                return {"status": "ok"}
        
        retrieval = MockRetrievalAgent("retrieval", a2a_manager)
        triage = TriageAgent("triage", a2a_manager, db_connection)
        
        # Test API auth failure classification
        ticket = Ticket(
            ticket_id="TKT-001",
            text="Getting 401 unauthorized errors",
            user_ref="alice@example.com"
        )
        
        triage.process_ticket(ticket)
        
        assert ticket.context["intent"] == "API Authentication Failure"
        assert ticket.context["confidence_score"] > 0.8
    
    def test_priority_assignment(self, a2a_manager, db_connection):
        """Test priority assignment based on tier and intent."""
        class MockRetrievalAgent(BaseA2AAgent):
            def handle_message(self, from_agent, message):
                return {"status": "ok"}
        
        retrieval = MockRetrievalAgent("retrieval", a2a_manager)
        triage = TriageAgent("triage", a2a_manager, db_connection)
        
        # Platinum user with critical issue should get P1
        ticket = Ticket(
            ticket_id="TKT-001",
            text="API 401 error",
            user_ref="alice@example.com"
        )
        
        triage.process_ticket(ticket)
        
        assert ticket.context["priority"] == "P1"


class TestRetrievalAgent:
    """Tests for retrieval agent."""
    
    def test_kb_matching(self, a2a_manager, db_connection):
        """Test knowledge base matching."""
        class MockEscalationAgent(BaseA2AAgent):
            def handle_message(self, from_agent, message):
                return {"status": "ok"}
        
        escalation = MockEscalationAgent("escalation", a2a_manager)
        retrieval = RetrievalAgent("retrieval", a2a_manager, db_connection)
        
        ticket = Ticket(
            ticket_id="TKT-001",
            text="Getting 401 errors",
            user_ref="test@example.com"
        )
        ticket.context = {"intent": "API Authentication Failure", "confidence_score": 0.6}
        
        message = A2AMessage(
            message_type=MessageType.REQUEST,
            from_agent="triage",
            to_agent="retrieval",
            payload={"type": "triage.complete", "ticket": ticket}
        )
        
        retrieval.handle_message("triage", message)
        
        assert ticket.context["kb_match"] is not None
        assert ticket.context["kb_match"]["issue_key"] == "api-auth-401"
        assert ticket.context["confidence_score"] > 0.6  # Boosted


class TestEscalationAgent:
    """Tests for escalation agent."""
    
    def test_auto_resolve_high_confidence(self, a2a_manager, db_connection):
        """Test auto-resolution for high confidence tickets."""
        escalation = EscalationAgent("escalation", a2a_manager, db_connection)
        
        ticket = Ticket(
            ticket_id="TKT-001",
            text="API issue",
            user_ref="alice@example.com"
        )
        ticket.user_id = 1
        ticket.user_email = "alice@example.com"
        ticket.context = {
            "tier": "PLATINUM",
            "renewal_active": True,
            "confidence_score": 0.9,
            "intent": "API Authentication Failure",
            "diagnostic_reasoning": "Check API key"
        }
        
        message = A2AMessage(
            message_type=MessageType.REQUEST,
            from_agent="retrieval",
            to_agent="escalation",
            payload={"type": "retrieval.complete", "ticket": ticket}
        )
        
        escalation.handle_message("retrieval", message)
        
        assert ticket.status == "Resolved"
    
    def test_escalate_low_confidence(self, a2a_manager, db_connection):
        """Test escalation for low confidence tickets."""
        escalation = EscalationAgent("escalation", a2a_manager, db_connection)
        
        ticket = Ticket(
            ticket_id="TKT-001",
            text="Something is wrong",
            user_ref="alice@example.com"
        )
        ticket.user_id = 1
        ticket.user_email = "alice@example.com"
        ticket.context = {
            "tier": "PLATINUM",
            "renewal_active": True,
            "confidence_score": 0.5,
            "intent": "General Question"
        }
        
        message = A2AMessage(
            message_type=MessageType.REQUEST,
            from_agent="retrieval",
            to_agent="escalation",
            payload={"type": "retrieval.complete", "ticket": ticket}
        )
        
        escalation.handle_message("retrieval", message)
        
        assert ticket.status == "Escalated"
    
    def test_pause_inactive_subscription(self, a2a_manager, db_connection):
        """Test pausing tickets for inactive subscriptions."""
        escalation = EscalationAgent("escalation", a2a_manager, db_connection)
        
        ticket = Ticket(
            ticket_id="TKT-001",
            text="Need help",
            user_ref="carol@example.com"
        )
        ticket.user_id = 3
        ticket.user_email = "carol@example.com"
        ticket.context = {
            "tier": "SILVER",
            "renewal_active": False,
            "confidence_score": 0.7
        }
        
        message = A2AMessage(
            message_type=MessageType.REQUEST,
            from_agent="retrieval",
            to_agent="escalation",
            payload={"type": "retrieval.complete", "ticket": ticket}
        )
        
        escalation.handle_message("retrieval", message)
        
        assert ticket.status == "Paused"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
