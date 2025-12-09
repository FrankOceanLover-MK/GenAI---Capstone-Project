import streamlit as st
import requests
from .utils import DEFAULT_BASE

def render(vin: str = None):
    """
    Renders the chat interface.
    
    Args:
        vin (str, optional): The VIN of the currently selected car, if any.
                             This allows the AI to answer specific questions about that car.
    """
    st.subheader("💬 AI Assistant")

    # 1. Initialize chat history in session state if it doesn't exist
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 2. Display existing chat messages from history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 3. Handle new user input
    if prompt := st.chat_input("Ask about a car, or ask for a recommendation..."):
        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(prompt)
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # 4. Call Backend API
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # Prepare payload matching backend ChatRequest schema
                    # If vin is None, we send null (so the backend triggers 'Search Mode')
                    payload = {
                        "question": prompt,
                        "vin": vin if vin else None 
                    }
                    
                    response = requests.post(
                        f"{DEFAULT_BASE}/chat", 
                        json=payload, 
                        timeout=30
                    )
                    
                    # Handle Errors
                    if response.status_code != 200:
                        error_msg = f"⚠️ Server returned error {response.status_code}: {response.text}"
                        st.error(error_msg)
                        return

                    # Parse success response
                    data = response.json()
                    answer = data.get("answer", "I couldn't generate a response.")
                    
                    # Display AI response
                    st.markdown(answer)
                    
                    # Add AI response to history
                    st.session_state.messages.append({"role": "assistant", "content": answer})

                except requests.exceptions.ConnectionError:
                    st.error("⚠️ Could not connect to backend. Is it running?")
                except Exception as e:
                    st.error(f"⚠️ An error occurred: {str(e)}")