import streamlit as st
import requests
import uuid

# Page config
st.set_page_config(
    page_title="Customer Support Agent",
    page_icon="🤖",
    layout="wide"
)

# Sidebar for settings
with st.sidebar:
    st.title("Settings")
    user_email = st.text_input("User Email", value="alice@example.com")
    session_id = st.text_input("Session ID", value="default_session")
    if st.button("New Session"):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()
    
    st.markdown("---")
    st.markdown("### capabilities")
    st.markdown("- 📊 Analytics")
    st.markdown("- 💳 Billing")
    st.markdown("- 🔄 Subscriptions")
    st.markdown("- 📚 Knowledge Base")

# Main chat interface
st.title("🤖 AI Customer Support")
st.markdown("Ask me about your subscription, invoices, or our policies.")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("How can I help you today?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("Thinking...")
        
        try:
            # Call FastAPI backend
            response = requests.post(
                "http://localhost:8000/query",
                json={
                    "text": prompt,
                    "user_email": user_email,
                    "session_id": session_id
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                # Handle both simple string response and JSON string response
                full_response = data.get("message", data.get("response", "No response"))
                message_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            else:
                error_msg = f"Error: {response.status_code} - {response.text}"
                message_placeholder.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
                
        except Exception as e:
            error_msg = f"Connection Error: {str(e)}"
            message_placeholder.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
