from google.adk import Agent
from model_config import get_model_config
from tools.billing_tools import (
    generate_invoice,
    get_unpaid_invoices,
    mark_invoice_paid
)

billing_agent = Agent(
    name="BillingAgent",
    description="Manages invoices, payments, and billing inquiries.",
    instruction="""
    You are the Billing Agent. You handle invoice generation, payment status checks, and listing unpaid invoices.
    
    Rules:
    1. When asked for unpaid invoices, use 'get_unpaid_invoices'.
    2. When generating an invoice, ensure the amount is positive.
    3. Provide clear summaries of financial data.
    """,
    tools=[
        generate_invoice,
        get_unpaid_invoices,
        mark_invoice_paid
    ],
    model=get_model_config()
)
