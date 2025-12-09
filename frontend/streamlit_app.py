import streamlit as st
from components.utils import (
    health,
    ask_chat,
    ApiError,
    DEFAULT_BASE,
)

st.set_page_config(
    page_title="Carwise AI - Your Smart Car Shopping Assistant",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Enhanced global styling with better hierarchy and consistency
st.markdown(
    """
    <style>
    /* Base styles */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: #ffffff;
    }

    .block-container {
        padding-top: 3rem;
        padding-bottom: 3rem;
        max-width: 900px;
    }

    /* Glass card effect - consistent across all cards */
    .glass-card {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 2rem;
        border: 1px solid rgba(255, 255, 255, 0.2);
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        margin-bottom: 1.5rem;
    }

    /* Header styles */
    .main-header {
        font-size: 2.8rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        text-align: center;
        background: linear-gradient(to right, #fff, #e0e7ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .sub-header {
        font-size: 1.1rem;
        opacity: 0.9;
        text-align: center;
        margin-bottom: 2rem;
    }

    /* Chat message styling */
    .stChatMessage {
        background: rgba(255, 255, 255, 0.15) !important;
        border-radius: 15px !important;
        padding: 1rem !important;
        margin-bottom: 1rem !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }

    /* Input styling */
    .stTextInput > div > div > input,
    .stChatInput > div > textarea {
        background: rgba(255, 255, 255, 0.2) !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        border-radius: 15px !important;
        color: white !important;
        padding: 1rem !important;
    }

    .stTextInput > div > div > input::placeholder,
    .stChatInput > div > textarea::placeholder {
        color: rgba(255, 255, 255, 0.6) !important;
    }

    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.75rem 2rem !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2) !important;
    }

    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3) !important;
    }

    /* Info box styling */
    .info-card {
        background: rgba(255, 255, 255, 0.15);
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid #667eea;
    }

    /* Listing card styling */
    .listing-card {
        background: rgba(255, 255, 255, 0.12);
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid rgba(255, 255, 255, 0.2);
        transition: all 0.3s ease;
    }

    .listing-card:hover {
        background: rgba(255, 255, 255, 0.18);
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
    }

    /* Hide default streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Improve dataframe styling */
    .stDataFrame {
        background: rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize session state
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "backend_healthy" not in st.session_state:
    try:
        health()
        st.session_state.backend_healthy = True
    except:
        st.session_state.backend_healthy = False

# Header section
st.markdown('<h1 class="main-header">🚗 Carwise AI</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-header">Your intelligent car shopping assistant powered by real-time data</p>',
    unsafe_allow_html=True
)

# Backend status indicator (subtle, top-right)
if not st.session_state.backend_healthy:
    st.error("⚠️ Backend is not reachable. Please ensure the FastAPI server is running.")
    st.stop()

# Main chat interface
st.markdown('<div class="glass-card">', unsafe_allow_html=True)

# Show example prompts if chat is empty
if not st.session_state.chat_messages:
    st.markdown("### 💬 What are you looking for?")
    st.markdown("**Try asking:**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🏠 Family SUV under $30k"):
            st.session_state.quick_prompt = "I need a reliable family SUV with good safety ratings under $30,000"
            st.rerun()
    
    with col2:
        if st.button("⚡ Fuel-efficient sedan"):
            st.session_state.quick_prompt = "Show me fuel-efficient sedans with at least 35 MPG"
            st.rerun()
    
    with col3:
        if st.button("🚙 Nearby used trucks"):
            st.session_state.quick_prompt = "I'm looking for used pickup trucks within 50 miles"
            st.rerun()

# Display chat history
for msg in st.session_state.chat_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        # Display listings if present
        if msg["role"] == "assistant" and "listings" in msg:
            listings = msg["listings"]
            if listings:
                st.markdown("---")
                st.markdown("### 🎯 Top Matches")
                
                for idx, car in enumerate(listings[:3], 1):
                    with st.container():
                        st.markdown(f"""
                        <div class="listing-card">
                            <h4>#{idx} - {car.get('year')} {car.get('make')} {car.get('model')}</h4>
                            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.5rem; margin-top: 1rem;">
                                <div><strong>💰 Price:</strong> ${car.get('price', 'N/A'):,.0f}</div>
                                <div><strong>🛣️ Mileage:</strong> {car.get('mileage', 'N/A'):,.0f} mi</div>
                                <div><strong>⛽ Fuel:</strong> {car.get('fuel_type', 'N/A')}</div>
                                <div><strong>📍 Distance:</strong> {car.get('distance_miles', 'N/A'):.0f} mi</div>
                                <div><strong>🏙️ City MPG:</strong> {car.get('city_mpg', 'N/A')}</div>
                                <div><strong>🛣️ Hwy MPG:</strong> {car.get('highway_mpg', 'N/A')}</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if car.get('listing_url'):
                            st.link_button("🔗 View Full Listing", car['listing_url'])

st.markdown('</div>', unsafe_allow_html=True)

# Chat input
user_input = st.chat_input("Describe the car you're looking for...")

# Handle quick prompt from buttons
if "quick_prompt" in st.session_state:
    user_input = st.session_state.quick_prompt
    del st.session_state.quick_prompt

if user_input:
    # Add user message
    st.session_state.chat_messages.append({
        "role": "user",
        "content": user_input
    })
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # Get AI response
    with st.chat_message("assistant"):
        with st.spinner("🔍 Searching live listings and analyzing..."):
            try:
                reply = ask_chat(user_input, vin=None)
                
                answer = reply.get("answer", "I couldn't find a suitable response.")
                # Escape markdown to prevent italic text rendering
                st.write(answer)
                
                # Store assistant message with listings
                assistant_msg = {
                    "role": "assistant",
                    "content": answer
                }
                
                listings = reply.get("listings", [])
                if listings:
                    assistant_msg["listings"] = listings
                    
                    st.markdown("---")
                    st.markdown("### 🎯 Top Matches")
                    
                    for idx, car in enumerate(listings[:3], 1):
                        st.markdown(f"""
                        <div class="listing-card">
                            <h4>#{idx} - {car.get('year')} {car.get('make')} {car.get('model')}</h4>
                            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.5rem; margin-top: 1rem;">
                                <div><strong>💰 Price:</strong> ${car.get('price', 'N/A'):,.0f}</div>
                                <div><strong>🛣️ Mileage:</strong> {car.get('mileage', 'N/A'):,.0f} mi</div>
                                <div><strong>⛽ Fuel:</strong> {car.get('fuel_type', 'N/A')}</div>
                                <div><strong>📍 Distance:</strong> {car.get('distance_miles', 'N/A'):.0f} mi</div>
                                <div><strong>🏙️ City MPG:</strong> {car.get('city_mpg', 'N/A')}</div>
                                <div><strong>🛣️ Hwy MPG:</strong> {car.get('highway_mpg', 'N/A')}</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if car.get('listing_url'):
                            st.link_button("🔗 View Full Listing", car['listing_url'], key=f"link_{idx}")
                    
                    # Show filters used
                    filters = reply.get("filters", {})
                    if filters:
                        with st.expander("🔍 Search filters used"):
                            for key, val in filters.items():
                                if val is not None:
                                    st.write(f"**{key.replace('_', ' ').title()}:** {val}")
                
                st.session_state.chat_messages.append(assistant_msg)
                
            except ApiError as e:
                error_msg = f"Sorry, I encountered an error: {e.message}"
                st.error(error_msg)
                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "content": error_msg
                })
            except Exception as e:
                error_msg = "I'm having trouble connecting to the search service. Please make sure the backend server is running."
                st.error(error_msg)
                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "content": error_msg
                })

# Footer with tips
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown("""
### 💡 Tips for Better Results
- **Be specific** about your budget (e.g., "under $25,000")
- **Mention priorities** like fuel efficiency, safety, or cargo space
- **Include location preferences** if distance matters to you
- **Ask follow-ups** to refine your search
""")
st.markdown('</div>', unsafe_allow_html=True)

# Clear chat button in sidebar
with st.sidebar:
    st.title("⚙️ Settings")
    if st.button("🗑️ Clear Chat History"):
        st.session_state.chat_messages = []
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 📊 Backend Status")
    st.success("✅ Connected" if st.session_state.backend_healthy else "❌ Disconnected")
    st.caption(f"URL: {DEFAULT_BASE}")