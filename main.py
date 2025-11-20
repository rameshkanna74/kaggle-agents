import uvicorn
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server import app

def main():
    """
    Entry point for the application.
    """
    port = int(os.getenv("PORT", 8000))
    print(f"Starting ADK Agent Server on port {port}...")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)

if __name__ == "__main__":
    main()
