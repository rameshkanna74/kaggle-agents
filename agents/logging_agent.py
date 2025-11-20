from google.adk import Agent
from model_config import get_model_config
from tools.logging_tools import log_activity

logging_agent = Agent(
    name="LoggingAgent",
    description="Responsible for logging all user and agent activities to the database.",
    instruction="""
    You are the Logging Agent. Your sole purpose is to record actions taken by other agents or the user.
    You have access to the 'log_activity' tool.
    When asked to log something, extract the user_email, agent_name, action, and details, and call the tool.
    Always return a confirmation that the log was successful.
    """,
    tools=[log_activity],
    model=get_model_config()
)
