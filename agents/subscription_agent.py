from google.adk import Agent
from model_config import get_model_config
from tools.subscription_tools import (
    get_user,
    cancel_subscription,
    postpone_subscription,
    upgrade_subscription,
    downgrade_subscription
)

subscription_agent = Agent(
    name="SubscriptionAgent",
    description="Handles all subscription-related queries and modifications.",
    instruction="""
    You are the Subscription Agent. You handle upgrades, downgrades, cancellations, and postponements.
    
    Rules:
    1. Always verify the user exists using 'get_user' before making changes if the user details aren't fully clear.
    2. For cancellations, downgrades, or postponements, you must ensure the user has confirmed their intent (though the Coordinator/Compliance agent handles the high-level check, you execute the tool).
    3. Return clear, human-readable responses summarizing the action taken.
    """,
    tools=[
        get_user,
        cancel_subscription,
        postpone_subscription,
        upgrade_subscription,
        downgrade_subscription
    ],
    model=get_model_config()
)
