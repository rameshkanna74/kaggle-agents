import os
from dotenv import load_dotenv

load_dotenv()

# Default model to use for all agents
# In a real scenario, you might use different models for different agents
DEFAULT_MODEL = "gemini-1.5-pro"

def get_model_config():
    """Returns the model configuration string or object."""
    # ADK accepts a string for Google models
    return os.getenv("MODEL_NAME", DEFAULT_MODEL)
