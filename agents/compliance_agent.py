from google.adk import Agent
from model_config import get_model_config
from tools.compliance_tools import (
    validate_action,
    hitl_confirmation
)

compliance_agent = Agent(
    name="ComplianceAgent",
    description="Ensures actions comply with business rules and safety checks.",
    instruction="""
    You are the Compliance Agent. You are the gatekeeper for sensitive actions.
    
    Rules:
    1. Use 'validate_action' to check if a requested move (like downgrade) is allowed.
    2. Use 'hitl_confirmation' for DESTRUCTIVE actions:
       - Cancellation
       - Refunds (if implemented)
       - Tier downgrades
    3. If validation fails or HITL is rejected, return a clear refusal message.
    4. If approved, return a success signal so the Coordinator can proceed.
    """,
    tools=[
        validate_action,
        hitl_confirmation
    ],
    model=get_model_config()
)
