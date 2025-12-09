import streamlit as st

from components.vin_input import render as render_vin
from components.filters import render as render_filters
from components.charts import table as render_table, mpg_chart
from components.utils import (
    try_recommendations,
    openapi_has_recommendations,
    ApiError,
    DEFAULT_BASE,
    health,
    ask_chat,
)

st.set_page_config(page_title="Carwise AI", layout="wide")


def render_general_chat():
    st.markdown('<div class="glass-header">Ask Carwise AI</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="glass-subtitle">'
        "Describe the kind of car you want. The assistant will search live listings and explain the best options."
        "</div>",
        unsafe_allow_html=True,
    )

    # keep chat history in session
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    # show previous messages
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # new user message
    user_text = st.chat_input("Describe what you are looking for")
    if not user_text:
        return

    user_text = user_text.strip()
    if not user_text:
        return

    # add and display user bubble
    st.session_state.chat_messages.append(
        {"role": "user", "content": user_text}
    )
    with st.chat_message("user"):
        st.write(user_text)

    # call backend chat, which already uses LLM plus search
    answer_text = "Something went wrong."
    with st.chat_message("assistant"):
        with st.spinner("Asking Carwise AI and searching live listings"):
            try:
                reply = ask_chat(user_text, vin=None)

                answer_text = reply.get("answer") or "No answer returned."
                st.write(answer_text)

                filters = reply.get("filters") or {}
                if filters:
                    st.markdown("**Filters the AI inferred**")
                    cols = st.columns(len(filters))
                    for i, (key, val) in enumerate(filters.items()):
                        with cols[i]:
                            st.caption(key)
                            st.code(str(val))

                listings = reply.get("listings") or []
                if listings:
                    st.markdown("**Top matches**")
                    render_table(listings)

            except ApiError as e:
                answer_text = f"Sorry, the backend returned an error: {e.message}"
                st.error(e.message)
            except Exception:
                answer_text = "Chat request failed. Check that your LLM server is running."
                st.error(answer_text)

    # persist assistant reply so it shows up on next rerun
    st.session_state.chat_messages.append(
        {"role": "assistant", "content": answer_text}
    )


# global styling
st.markdown(
    """
    <style>
    .stApp {
        background: radial-gradient(circle at top left, #4e54c8 0, #1f1c2c 35, #141321 100);
        color: #f5f5ff;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }

    .glass-card {
        background: rgba(10, 12, 28, 0.85);
        border-radius: 18px;
        padding: 20px 22px 18px 22px;
        border: 1px solid rgba(255, 255, 255, 0.06);
        box-shadow: 0 20px 45px rgba(0, 0, 0, 0.55);
        backdrop-filter: blur(14px);
    }

    .glass-header {
        font-size: 1.4rem;
        font-weight: 600;
        margin-bottom: 0.25rem;
    }

    .glass-subtitle {
        font-size: 0.9rem;
        opacity: 0.8;
        margin-bottom: 1rem;
    }

    .stButton>button {
        border-radius: 999px;
        font-weight: 600;
    }

    .stTextInput>div>div>input {
        border-radius: 999px;
    }

    .stNumberInput>div>div>input {
        border-radius: 999px;
    }

    .stSelectbox>div>div>select {
        border-radius: 999px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# sidebar
st.sidebar.title("Carwise AI backend")
st.sidebar.write("Base URL")
st.sidebar.code(DEFAULT_BASE)
try:
    h = health()
    st.sidebar.success("Backend healthy")
    if isinstance(h, dict) and h.get("mode"):
        st.sidebar.write(f"Mode {h['mode']}")
except Exception:
    st.sidebar.error("Backend not reachable")

# top title card
st.markdown(
    """
    <div class="glass-card">
        <div class="glass-header">Carwise AI</div>
        <div class="glass-subtitle">
            Talk to the assistant about what you need in a car. It will search live listings and use VIN lookup as a bonus tool.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")

# chat card
st.markdown('<div class="glass-card">', unsafe_allow_html=True)

chat_mode = st.radio(
    "Conversation mode",
    ["General discovery", "Talk about the last VIN"],
    horizontal=True,
)

if chat_mode == "General discovery":
    render_general_chat()
else:
    st.markdown('<div class="glass-header">Ask about the last VIN</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="glass-subtitle">'
        "Ask follow up questions about the car you looked up in the VIN panel below."
        "</div>",
        unsafe_allow_html=True,
    )

    last_vin = st.session_state.get("last_vin")
    if not last_vin:
        st.info("Look up a VIN in the panel below first.")

    q = st.text_input("Ask a question about the last VIN", value="")
    if st.button("Ask about VIN", type="primary", key="ask_vin"):
        if not last_vin:
            st.warning("No VIN stored yet.")
        elif not q.strip():
            st.warning("Please enter a question.")
        else:
            with st.spinner("Asking Carwise AI about this car"):
                try:
                    reply = ask_chat(q.strip(), vin=last_vin)
                    st.write("**Answer**")
                    st.write(reply.get("answer") or "No answer returned.")
                except ApiError as e:
                    st.error(e.message)
                except Exception:
                    st.error("Chat request failed. Check that your LLM server is running.")

st.markdown("</div>", unsafe_allow_html=True)

st.write("")

# two columns for VIN lookup and recommendations table
left, right = st.columns(2, gap="large")

with left:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="glass-header">VIN lookup</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="glass-subtitle">Use this when you already have a VIN and want details.</div>',
        unsafe_allow_html=True,
    )
    car, last_vin = render_vin()
    if last_vin:
        st.session_state["last_vin"] = last_vin
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="glass-header">Recommendations table</div>', unsafe_allow_html=True)

    if openapi_has_recommendations():
        run, params = render_filters()
        if run:
            with st.spinner("Fetching recommendations from backend"):
                try:
                    path, data = try_recommendations(params)
                    if isinstance(data, list) and data:
                        df = render_table(data)
                        mpg_chart(df)
                    else:
                        st.warning("No recommendations returned.")
                except ApiError as e:
                    st.error(e.message)
                except Exception:
                    st.error("Failed to contact recommendations endpoint.")
    else:
        st.info(
            "Recommendations endpoint not available on backend yet. "
            "This panel will enable automatically once the backend exposes /search."
        )

    st.markdown("</div>", unsafe_allow_html=True)
