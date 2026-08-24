"""
app.py — Oulu Restaurant AI Chatbot
Beautiful, colorful UI with custom CSS
"""

import streamlit as st
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent))

st.set_page_config(
    page_title="Oulu Restaurant AI",
    page_icon="🍛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Serif+Display&display=swap');

/* ── Global ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

/* ── Main background ── */
.stApp {
    background: linear-gradient(135deg, #faf7ff 0%, #f0edff 50%, #edf4ff 100%);
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a0533 0%, #0d0020 100%) !important;
    border-right: 1px solid rgba(170,59,255,0.2);
}
[data-testid="stSidebar"] * { color: #e8d5ff !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #ffffff !important; }
[data-testid="stSidebar"] .stMarkdown a { color: #c084ff !important; }
[data-testid="stSidebar"] hr { border-color: rgba(170,59,255,0.3) !important; }

/* Sidebar buttons */
[data-testid="stSidebar"] .stButton button {
    background: rgba(170,59,255,0.12) !important;
    border: 1px solid rgba(170,59,255,0.3) !important;
    color: #e8d5ff !important;
    border-radius: 8px !important;
    font-size: 0.8rem !important;
    text-align: left !important;
    transition: all 0.2s !important;
}
[data-testid="stSidebar"] .stButton button:hover {
    background: rgba(170,59,255,0.25) !important;
    border-color: #aa3bff !important;
    color: #ffffff !important;
    transform: translateX(4px) !important;
}

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    background: rgba(255,255,255,0.75) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px solid rgba(170,59,255,0.12) !important;
    border-radius: 16px !important;
    box-shadow: 0 2px 16px rgba(170,59,255,0.06) !important;
    margin-bottom: 0.75rem !important;
    padding: 1rem !important;
}

/* User message — blue tint */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: rgba(237,244,255,0.9) !important;
    border-color: rgba(99,102,241,0.2) !important;
}

/* ── Chat input ── */
[data-testid="stChatInput"] {
    background: rgba(255,255,255,0.9) !important;
    border: 2px solid rgba(170,59,255,0.25) !important;
    border-radius: 100px !important;
    box-shadow: 0 4px 24px rgba(170,59,255,0.12) !important;
}
[data-testid="stChatInput"]:focus-within {
    border-color: #aa3bff !important;
    box-shadow: 0 4px 24px rgba(170,59,255,0.25) !important;
}

/* ── Spinner ── */
.stSpinner > div { border-top-color: #aa3bff !important; }

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.7) !important;
    border-radius: 12px !important;
    padding: 0.75rem 1rem !important;
    border: 1px solid rgba(170,59,255,0.12) !important;
}

/* ── Alerts ── */
.stAlert { border-radius: 12px !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: rgba(170,59,255,0.3);
    border-radius: 100px;
}
::-webkit-scrollbar-thumb:hover { background: #aa3bff; }

/* ── Badge pills ── */
.badge {
    display: inline-block;
    padding: 0.2rem 0.65rem;
    border-radius: 100px;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.05em;
}
.badge-purple { background: rgba(170,59,255,0.12); color: #7c22c4; }
.badge-teal   { background: rgba(13,148,136,0.12);  color: #0f766e; }
.badge-green  { background: rgba(16,185,129,0.12);  color: #047857; }
.badge-blue   { background: rgba(99,102,241,0.12);  color: #3730a3; }

/* ── Welcome card ── */
.welcome-card {
    background: linear-gradient(135deg, #aa3bff 0%, #6366f1 100%);
    border-radius: 20px;
    padding: 2rem 2.5rem;
    color: white;
    margin-bottom: 1.5rem;
    box-shadow: 0 8px 32px rgba(170,59,255,0.3);
}
.welcome-card h2 { color: white; font-family: 'DM Serif Display', serif; margin: 0 0 0.5rem; font-size: 1.6rem; }
.welcome-card p  { color: rgba(255,255,255,0.85); margin: 0; font-size: 0.95rem; line-height: 1.6; }

/* ── Capability cards ── */
.cap-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; margin: 1rem 0 1.5rem; }
.cap-card {
    border-radius: 14px;
    padding: 1rem 1.1rem;
    border: 1px solid transparent;
    transition: transform 0.2s, box-shadow 0.2s;
    cursor: default;
}
.cap-card:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,0.08); }
.cap-card-1 { background: linear-gradient(135deg,#f5edff,#ede0ff); border-color: rgba(170,59,255,0.2); }
.cap-card-2 { background: linear-gradient(135deg,#e6faf8,#d4f4f0); border-color: rgba(13,148,136,0.2); }
.cap-card-3 { background: linear-gradient(135deg,#fff0f3,#ffe4ea); border-color: rgba(244,63,94,0.2); }
.cap-card-4 { background: linear-gradient(135deg,#fff7ed,#fde8c8); border-color: rgba(245,158,11,0.2); }
.cap-card-5 { background: linear-gradient(135deg,#eef2ff,#e0e7ff); border-color: rgba(99,102,241,0.2); }
.cap-card-6 { background: linear-gradient(135deg,#f0fdf4,#dcfce7); border-color: rgba(16,185,129,0.2); }
.cap-icon  { font-size: 1.5rem; margin-bottom: 0.4rem; }
.cap-title { font-size: 0.82rem; font-weight: 700; color: #0f0a1e; margin: 0 0 0.2rem; }
.cap-desc  { font-size: 0.72rem; color: #6b7280; margin: 0; line-height: 1.4; }

/* ── Tech stack badges ── */
.tech-row {
    display: flex; flex-wrap: wrap; gap: 0.4rem;
    padding: 0.75rem 0; margin-bottom: 0.5rem;
}
.tech-pill {
    font-size: 0.68rem; font-weight: 600;
    padding: 0.2rem 0.6rem; border-radius: 100px;
    background: rgba(255,255,255,0.8);
    border: 1px solid rgba(170,59,255,0.2);
    color: #4a4560;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def get_secret(key: str) -> str:
    try:
        return st.secrets.get(key) or ""
    except Exception:
        import os
        return os.environ.get(key, "")


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:1rem 0 0.5rem;">
        <p style="font-size:1.6rem;margin:0;">🍛</p>
        <h2 style="font-family:'DM Serif Display',serif;font-size:1.3rem;
                   margin:0.3rem 0 0.2rem;color:#fff;">Oulu Restaurant AI</h2>
        <p style="font-size:0.78rem;color:rgba(232,213,255,0.7);margin:0;">
            Find · Order · Book · Discover
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.markdown("### 🏪 Restaurants")
    restaurants = [
        ("🇵🇰", "Punjabi Taste", "Pakistani/Indian"),
        ("🇳🇵", "Sauraha", "Nepali/Indian"),
        ("🇧🇩", "Badipur", "Indian/Bangladeshi"),
        ("🇮🇳", "Garam Masala", "South Indian"),
        ("🇱🇰", "Spice Garden", "Indian/Sri Lankan"),
    ]
    for flag, name, cuisine in restaurants:
        st.markdown(
            f'<div style="padding:0.3rem 0;">'
            f'<span style="font-size:1rem;">{flag}</span> '
            f'<strong style="color:#fff;">{name}</strong>'
            f'<br><span style="font-size:0.72rem;color:rgba(232,213,255,0.6);">{cuisine}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.divider()
    st.markdown("### 💡 Try asking")

    suggestions = [
        ("🥗", "Best restaurant for vegans?"),
        ("🍽️", "Show me Punjabi Taste menu"),
        ("🛵", "Order butter chicken for delivery"),
        ("📅", "Book table for 2 on Friday"),
        ("⭐", "What do reviews say about lamb curry?"),
        ("📦", "Check my order status"),
    ]
    for icon, text in suggestions:
        if st.button(f"{icon} {text}", key=f"s_{text}", use_container_width=True):
            st.session_state.pending = text

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    with col2:
        st.markdown(
            '<a href="https://github.com/swat90/oulu-restaurant-chatbot" '
            'target="_blank" style="text-decoration:none;">'
            '<button style="width:100%;background:rgba(170,59,255,0.15);'
            'border:1px solid rgba(170,59,255,0.4);color:#e8d5ff;'
            'border-radius:8px;padding:0.4rem;font-size:0.8rem;cursor:pointer;">'
            '⭐ GitHub</button></a>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<p style="font-size:0.68rem;color:rgba(232,213,255,0.4);'
        'text-align:center;margin-top:1rem;">'
        'Demo · Supabase + Gemini + pgvector</p>',
        unsafe_allow_html=True,
    )


# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending" not in st.session_state:
    st.session_state.pending = None


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:1rem;padding:0.5rem 0 1rem;">
  <div>
    <h1 style="font-family:'DM Serif Display',serif;font-size:2rem;
               margin:0;background:linear-gradient(135deg,#aa3bff,#6366f1);
               -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
      Oulu Restaurant AI
    </h1>
    <p style="margin:0;color:#6b7280;font-size:0.88rem;">
      Powered by Gemini 3.5 Flash · LangChain · Supabase · pgvector
    </p>
  </div>
</div>
""", unsafe_allow_html=True)

# Tech pills
st.markdown("""
<div class="tech-row">
  <span class="tech-pill">🤖 Gemini 2.0 Flash</span>
  <span class="tech-pill">⛓️ LangChain Agent</span>
  <span class="tech-pill">🗄️ Supabase PostgreSQL</span>
  <span class="tech-pill">🔍 pgvector RAG</span>
  <span class="tech-pill">📧 Email Receipts</span>
  <span class="tech-pill">🔄 CircleCI CI/CD</span>
</div>
""", unsafe_allow_html=True)


# ── Check secrets ─────────────────────────────────────────────────────────────
missing = []
if not get_secret("SUPABASE_URL"):   missing.append("SUPABASE_URL")
if not get_secret("SUPABASE_KEY"):   missing.append("SUPABASE_KEY")
if not get_secret("GEMINI_API_KEY"): missing.append("GEMINI_API_KEY")

if missing:
    st.error(
        f"⚠️ Missing secrets: **{', '.join(missing)}**\n\n"
        "Add them in `.streamlit/secrets.toml` or Streamlit Cloud settings."
    )
    st.stop()


# ── Welcome screen (shown when no messages) ───────────────────────────────────
if not st.session_state.messages:
    st.markdown("""
    <div class="welcome-card">
      <h2>👋 Welcome! I'm your Oulu restaurant assistant.</h2>
      <p>I can find restaurants, show menus, place food orders with email receipts,
         book tables saved to a real database, and answer questions from customer reviews.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="cap-grid">
      <div class="cap-card cap-card-1">
        <div class="cap-icon">🔍</div>
        <p class="cap-title">Find Restaurants</p>
        <p class="cap-desc">By cuisine, dietary needs, features or location</p>
      </div>
      <div class="cap-card cap-card-2">
        <div class="cap-icon">🍽️</div>
        <p class="cap-title">Browse Menus</p>
        <p class="cap-desc">Prices, dietary flags, spice levels</p>
      </div>
      <div class="cap-card cap-card-3">
        <div class="cap-icon">🛵</div>
        <p class="cap-title">Place Orders</p>
        <p class="cap-desc">Delivery or pickup · saved to DB · email receipt</p>
      </div>
      <div class="cap-card cap-card-4">
        <div class="cap-icon">📅</div>
        <p class="cap-title">Book Tables</p>
        <p class="cap-desc">Real-time availability · booking ref · email</p>
      </div>
      <div class="cap-card cap-card-5">
        <div class="cap-icon">⭐</div>
        <p class="cap-title">Review Insights</p>
        <p class="cap-desc">Semantic search over real customer reviews</p>
      </div>
      <div class="cap-card cap-card-6">
        <div class="cap-icon">📦</div>
        <p class="cap-title">Manage Orders</p>
        <p class="cap-desc">Look up bookings and orders by reference</p>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(
        '<p style="text-align:center;color:#8b82a8;font-size:0.85rem;">'
        '👇 Type below or click a suggestion in the sidebar</p>',
        unsafe_allow_html=True,
    )


# ── Chat history ──────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    avatar = "🧑" if msg["role"] == "user" else "🍛"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])


# ── Input ─────────────────────────────────────────────────────────────────────
user_input = st.chat_input("Ask me anything about Oulu's Indian restaurants...")

if st.session_state.pending:
    user_input = st.session_state.pending
    st.session_state.pending = None

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(user_input)

    with st.chat_message("assistant", avatar="🍛"):
        with st.spinner(""):
            try:
                import agent
                response = agent.chat(user_input, st.session_state.messages)
            except ValueError as e:
                response = f"⚠️ **Configuration error:** {e}"
            except Exception as e:
                response = f"⚠️ **Error:** {str(e)}\n\nPlease try again."
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
