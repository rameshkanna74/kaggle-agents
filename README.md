# Multi-Agent Customer Support Platform

This project implements an advanced multi-agent customer support system using Google ADK (Agent Development Kit).

## Architecture

- **CoordinatorAgent**: Routes queries and manages the workflow.
- **SubscriptionAgent**: Handles subscription changes.
- **BillingAgent**: Manages invoices and payments.
- **ComplianceAgent**: Validates actions and requires HITL approval.
- **LoggingAgent**: Logs all activities.
- **AnalyticsAgent**: Provides insights.

## Setup

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Initialize Database**:
    ```bash
    python db/seed.py
    ```

3.  **Run Server**:
    ```bash
    python main.py
    ```
    Or directly with uvicorn:
    ```bash
    uvicorn server:app --reload
    ```

## Docker

1.  **Build**:
    ```bash
    docker build -t adk-support-agent .
    ```

2.  **Run**:
    ```bash
    docker run -p 8000:8000 adk-support-agent
    ```

## Usage

Send a POST request to `/query`:

```bash
curl -X POST "http://localhost:8000/query" \
     -H "Content-Type: application/json" \
     -d '{"text": "Cancel my subscription. My email is pro_user@example.com."}'
```

## Deployment to Cloud Run

1.  **Build and Push**:
    ```bash
    gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/adk-support-agent
    ```

2.  **Deploy**:
    ```bash
    gcloud run deploy adk-support-agent \
      --image gcr.io/YOUR_PROJECT_ID/adk-support-agent \
      --platform managed \
      --allow-unauthenticated
    ```
