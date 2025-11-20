from google.adk import Agent
from model_config import get_model_config

# Import all tools directly
from tools.subscription_tools import (
    get_user,
    cancel_subscription,
    postpone_subscription,
    upgrade_subscription,
    downgrade_subscription
)
from tools.billing_tools import (
    generate_invoice,
    get_unpaid_invoices,
    mark_invoice_paid
)
from tools.analytics_tools import (
    compute_monthly_revenue,
    compute_tier_distribution,
    compute_cancellation_rate
)
from tools.compliance_tools import (
    validate_action,
    hitl_confirmation
)
from tools.logging_tools import log_activity

# Create a single coordinator agent with all tools
coordinator_agent = Agent(
    name="CoordinatorAgent",
    description="The root decision-maker that handles all customer support queries.",
    instruction="""
    You are the Coordinator Agent for a customer support platform. You have access to all tools needed to help users.
    
    Your responsibilities:
    1. Analyze the user's request and determine what action is needed.
    2. Use the appropriate tools to fulfill the request:
       - For subscription queries: use get_user, cancel_subscription, postpone_subscription, upgrade_subscription, downgrade_subscription
       - For billing queries: use generate_invoice, get_unpaid_invoices, mark_invoice_paid
       - For analytics queries: use compute_monthly_revenue, compute_tier_distribution, compute_cancellation_rate
    3. BEFORE executing destructive actions (cancel, downgrade, refund):
       - Call validate_action to check if it's allowed
       - Call hitl_confirmation to get approval
       - If denied, inform the user
    4. AFTER any successful action that changes state:
       - Call log_activity to record it
    5. Provide clear, helpful responses in JSON format with keys: "status", "message", "data" (optional).
    
    Always extract the user's email from their request when needed for operations.
    """,
    tools=[
        # Subscription tools
        get_user,
        cancel_subscription,
        postpone_subscription,
        upgrade_subscription,
        downgrade_subscription,
        # Billing tools
        generate_invoice,
        get_unpaid_invoices,
        mark_invoice_paid,
        # Analytics tools
        compute_monthly_revenue,
        compute_tier_distribution,
        compute_cancellation_rate,
        # Compliance tools
        validate_action,
        hitl_confirmation,
        # Logging tools
        log_activity
    ],
    model=get_model_config()
)
