from google.adk import Agent
from model_config import get_model_config
from tools.analytics_tools import (
    compute_monthly_revenue,
    compute_tier_distribution,
    compute_cancellation_rate
)

analytics_agent = Agent(
    name="AnalyticsAgent",
    description="Provides insights and metrics about the platform's performance.",
    instruction="""
    You are the Analytics Agent. You calculate and report on system metrics.
    
    Capabilities:
    - Monthly revenue
    - User distribution by tier
    - Cancellation rates
    
    Present the data in a clean, summarized format.
    """,
    tools=[
        compute_monthly_revenue,
        compute_tier_distribution,
        compute_cancellation_rate
    ],
    model=get_model_config()
)
