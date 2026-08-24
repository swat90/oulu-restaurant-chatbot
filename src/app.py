"""
app.py — Oulu Restaurant AI Chatbot
Streamlit chat interface
Run: streamlit run src/app.py
"""

import streamlit as st
import sys
import pathlib

# Add src folder to path so imports work
sys.path.insert(0, str(pathlib.Path(__file__).parent))

st.set_page_config(
    page_title="Oulu Restaurant AI",
    page_icon="🍛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🍛 Oulu Restaurant AI")
    st.caption("Find restaurants, browse menus, and book tables — powered by AI")
    st.divider()

    st.markdown("### 🏪 Restaurants")
    st.markdown("""
- **Punjabi Taste** — Pakistani/Indian
- **Sauraha** — Nepali/Indian
- **Badipur** — Indian/Bangladeshi
- **Garam Masala** — South Indian
- **Spice Garden** — Indian/Sri Lankan
    """)

    st.divider()
    st.markdown("### 💡 Try asking:")

    suggestions = [
        "Which restaurant is best for vegans?",
        "Show me Punjabi Taste menu",
        "I want to order butter chicken and garlic naan for delivery",
        "Book a table for 2 at Garam Masala on Friday",
        "What do people say about the lamb curry?",
        "Check my order ORD-XXXXX",
    ]
    for s in suggestions:
        if st.button(s, key=f"btn_{s}", use_container_width=True):
            st.session_state.pending = s

    st.divider()
    if st.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.markdown("### 🛵 What I can do")
    st.markdown("""
- 🔍 Find restaurants
- 🍽️ Browse menus
- 📅 Check availability
- ✅ **Book a table** → saves to DB
- 🛵 **Place food order** → saves to DB + sends email receipt
- ⭐ Answer from real reviews
    """)
    st.caption("Demo — orders & bookings stored in real Supabase DB")

# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending" not in st.session_state:
    st.session_state.pending = None

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🍛 Oulu Restaurant Assistant")
st.caption(
    "Ask about restaurants · Browse menus · Check availability · Book a table"
)

# Tech stack pills
st.markdown(
    "**Stack:** `LangChain` `Gemini 2.0 Flash` `Supabase PostgreSQL` "
    "`pgvector RAG` `Streamlit`"
)
st.divider()

# ── Check secrets ─────────────────────────────────────────────────────────────
def get_secret(key):
    try:
        val = st.secrets.get(key, "")
        return val if val else ""
    except Exception:
        import os
        return os.environ.get(key, "")

missing = []
if not get_secret("SUPABASE_URL"):  missing.append("SUPABASE_URL")
if not get_secret("SUPABASE_KEY"):  missing.append("SUPABASE_KEY")
if not get_secret("GEMINI_API_KEY"): missing.append("GEMINI_API_KEY")

if missing:
    st.error(
        f"⚠️ Missing secrets: **{', '.join(missing)}**\n\n"
        "Create `.streamlit/secrets.toml` with:\n"
        "```toml\n"
        'SUPABASE_URL = "https://xxx.supabase.co"\n'
        'SUPABASE_KEY = "eyJhbGc..."\n'
        'GEMINI_API_KEY = "AIza..."\n'
        "```"
    )
    st.stop()

# ── Display chat history ──────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Welcome message ───────────────────────────────────────────────────────────
if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown("""
👋 **Welcome! I'm your Oulu restaurant assistant.**

I can help you:
- 🔍 **Find** restaurants by cuisine or dietary needs
- 🍽️ **Browse** menus with prices and dietary info
- 🛵 **Order food** for delivery or pickup — saved to database + email receipt
- 📅 **Book a table** — saved to database + email confirmation
- ⭐ **Answer** questions using real customer reviews

**What would you like to do?**
        """)

# ── Handle input ──────────────────────────────────────────────────────────────
user_input = st.chat_input("Ask me anything about Oulu's Indian restaurants...")

# Handle sidebar suggestion button
if st.session_state.pending:
    user_input = st.session_state.pending
    st.session_state.pending = None

if user_input:
    # Show user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Get agent response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                import agent
                response = agent.chat(
                    user_input,
                    st.session_state.messages,
                )
            except ValueError as e:
                # Config errors — show clearly
                response = f"⚠️ **Configuration error:** {e}"
            except Exception as e:
                err = str(e)
                # Show the actual error for debugging
                response = (
                    f"⚠️ **Error:** {err}\n\n"
                    "Please check the terminal for the full traceback."
                )
        st.markdown(response)

    st.session_state.messages.append({
        "role": "assistant",
        "content": response,
    })
