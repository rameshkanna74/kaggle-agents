"""
Agent-to-Agent (A2A) communication framework.

Enables decoupled communication between agents using message passing.
Based on the multiTechAgentFinal.ipynb reference implementation.

Features:
- Agent registry and discovery
- Request-response messaging
- Thread-safe message passing
- Timeout handling
- Error propagation
"""

import threading
import logging
from typing import Any, Dict, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import time

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of A2A messages."""
    REQUEST = "request"
    RESPONSE = "response"
    ERROR = "error"
    NOTIFICATION = "notification"


@dataclass
class A2AMessage:
    """Message passed between agents."""
    message_type: MessageType
    from_agent: str
    to_agent: str
    payload: Dict[str, Any]
    message_id: Optional[str] = None
    correlation_id: Optional[str] = None
    timestamp: Optional[float] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class A2AManager:
    """
    Central manager for agent-to-agent communication.
    
    Provides:
    - Agent registration
    - Message routing
    - Error handling
    - Thread safety
    """
    
    def __init__(self):
        """Initialize the A2A manager."""
        self._agents: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._message_handlers: Dict[str, Callable] = {}
    
    def register(self, name: str, agent_obj: Any) -> None:
        """
        Register an agent with the A2A system.
        
        Args:
            name: Unique name for the agent
            agent_obj: Agent instance (must have handle_message method)
        
        Raises:
            ValueError: If agent name already registered or invalid agent
        """
        with self._lock:
            if name in self._agents:
                raise ValueError(f"Agent '{name}' is already registered")
            
            # Verify agent has required interface
            if not hasattr(agent_obj, 'handle_message'):
                raise ValueError(
                    f"Agent '{name}' must have a 'handle_message' method"
                )
            
            self._agents[name] = agent_obj
            logger.info(f"[A2A] Registered agent '{name}'")
    
    def unregister(self, name: str) -> None:
        """
        Unregister an agent from the A2A system.
        
        Args:
            name: Name of the agent to unregister
        """
        with self._lock:
            if name in self._agents:
                del self._agents[name]
                logger.info(f"[A2A] Unregistered agent '{name}'")
    
    def send(
        self,
        from_agent: str,
        to_agent: str,
        payload: Dict[str, Any],
        message_type: MessageType = MessageType.REQUEST,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Send a message from one agent to another.
        
        Args:
            from_agent: Name of the sending agent
            to_agent: Name of the receiving agent
            payload: Message payload
            message_type: Type of message
            timeout: Optional timeout in seconds
        
        Returns:
            Response from the target agent
        
        Raises:
            RuntimeError: If target agent not found or message handling fails
            TimeoutError: If message handling exceeds timeout
        """
        with self._lock:
            if to_agent not in self._agents:
                raise RuntimeError(f"Agent '{to_agent}' not registered")
            
            target = self._agents[to_agent]
        
        # Create message
        message = A2AMessage(
            message_type=message_type,
            from_agent=from_agent,
            to_agent=to_agent,
            payload=payload
        )
        
        logger.debug(
            f"[A2A] {from_agent} -> {to_agent}: {message_type.value}"
        )
        
        try:
            # Handle message with optional timeout
            if timeout:
                result = self._handle_with_timeout(
                    target.handle_message,
                    from_agent,
                    message,
                    timeout
                )
            else:
                result = target.handle_message(from_agent, message)
            
            return result if result is not None else {"status": "ok"}
            
        except TimeoutError:
            logger.error(
                f"[A2A] Timeout handling message from {from_agent} to {to_agent}"
            )
            raise
        except Exception as e:
            logger.exception(
                f"[A2A] Error invoking {to_agent} from {from_agent}: {e}"
            )
            return {
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def _handle_with_timeout(
        self,
        handler: Callable,
        from_agent: str,
        message: A2AMessage,
        timeout: float
    ) -> Any:
        """
        Handle message with timeout using threading.
        
        Args:
            handler: Message handler function
            from_agent: Sending agent name
            message: Message to handle
            timeout: Timeout in seconds
        
        Returns:
            Handler result
        
        Raises:
            TimeoutError: If handler exceeds timeout
        """
        result = [None]
        exception = [None]
        
        def target():
            try:
                result[0] = handler(from_agent, message)
            except Exception as e:
                exception[0] = e
        
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout)
        
        if thread.is_alive():
            raise TimeoutError(f"Message handling exceeded {timeout}s timeout")
        
        if exception[0]:
            raise exception[0]
        
        return result[0]
    
    def broadcast(
        self,
        from_agent: str,
        payload: Dict[str, Any],
        exclude: Optional[list[str]] = None
    ) -> Dict[str, Any]:
        """
        Broadcast a message to all registered agents.
        
        Args:
            from_agent: Name of the sending agent
            payload: Message payload
            exclude: Optional list of agent names to exclude
        
        Returns:
            Dictionary mapping agent names to their responses
        """
        exclude = exclude or []
        responses = {}
        
        with self._lock:
            agents = list(self._agents.keys())
        
        for agent_name in agents:
            if agent_name == from_agent or agent_name in exclude:
                continue
            
            try:
                response = self.send(
                    from_agent,
                    agent_name,
                    payload,
                    MessageType.NOTIFICATION
                )
                responses[agent_name] = response
            except Exception as e:
                logger.error(
                    f"[A2A] Error broadcasting to {agent_name}: {e}"
                )
                responses[agent_name] = {"status": "error", "error": str(e)}
        
        return responses
    
    def list_agents(self) -> list[str]:
        """
        Get list of registered agent names.
        
        Returns:
            List of agent names
        """
        with self._lock:
            return list(self._agents.keys())
    
    def is_registered(self, name: str) -> bool:
        """
        Check if an agent is registered.
        
        Args:
            name: Agent name to check
        
        Returns:
            True if agent is registered
        """
        with self._lock:
            return name in self._agents


class BaseA2AAgent:
    """
    Base class for agents that participate in A2A communication.
    
    Subclasses must implement the handle_message method.
    """
    
    def __init__(self, name: str, a2a_manager: A2AManager):
        """
        Initialize the agent.
        
        Args:
            name: Unique name for this agent
            a2a_manager: A2A manager instance
        """
        self.name = name
        self.a2a = a2a_manager
        self.a2a.register(name, self)
        logger.info(f"[{name}] Initialized and registered with A2A")
    
    def handle_message(self, from_agent: str, message: A2AMessage) -> Dict[str, Any]:
        """
        Handle incoming A2A message.
        
        Must be implemented by subclasses.
        
        Args:
            from_agent: Name of the sending agent
            message: The A2A message
        
        Returns:
            Response dictionary
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement handle_message"
        )
    
    def send_to(
        self,
        target_agent: str,
        payload: Dict[str, Any],
        message_type: MessageType = MessageType.REQUEST
    ) -> Dict[str, Any]:
        """
        Send a message to another agent.
        
        Args:
            target_agent: Name of the target agent
            payload: Message payload
            message_type: Type of message
        
        Returns:
            Response from target agent
        """
        return self.a2a.send(self.name, target_agent, payload, message_type)
    
    def cleanup(self):
        """Cleanup and unregister from A2A system."""
        self.a2a.unregister(self.name)
        logger.info(f"[{self.name}] Cleaned up and unregistered")


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Create A2A manager
    a2a = A2AManager()
    
    # Example agent implementation
    class ExampleAgent(BaseA2AAgent):
        def handle_message(self, from_agent: str, message: A2AMessage) -> Dict[str, Any]:
            logger.info(
                f"[{self.name}] Received {message.message_type.value} from {from_agent}"
            )
            return {
                "status": "processed",
                "agent": self.name,
                "received_from": from_agent
            }
    
    # Create agents
    agent1 = ExampleAgent("agent1", a2a)
    agent2 = ExampleAgent("agent2", a2a)
    agent3 = ExampleAgent("agent3", a2a)
    
    print("\n=== A2A Communication Test ===\n")
    
    # Test direct messaging
    print("1. Direct message:")
    response = agent1.send_to("agent2", {"test": "data"})
    print(f"Response: {response}\n")
    
    # Test broadcast
    print("2. Broadcast message:")
    responses = a2a.broadcast("agent1", {"broadcast": "message"})
    print(f"Responses: {responses}\n")
    
    # Test agent listing
    print("3. Registered agents:")
    print(f"Agents: {a2a.list_agents()}\n")
    
    # Cleanup
    agent1.cleanup()
    agent2.cleanup()
    agent3.cleanup()
