# 🍛 Oulu Restaurant AI — Agentic Chatbot with Live Database

> **An end-to-end agentic AI system** that handles natural language restaurant queries,
> real-time table bookings, food ordering, and semantic review search —
> all backed by a live PostgreSQL database.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Streamlit-ff4b4b?style=for-the-badge&logo=streamlit)](https://oulu-restaurant-chatbot.streamlit.app)
[![Video Walkthrough](https://img.shields.io/badge/Video%20Walkthrough-Zight-6366f1?style=for-the-badge)](https://share.zight.com/01a0300c-76db-79a5-a84d-d8e6b21a80ae)
[![Python](https://img.shields.io/badge/Python-3.11-3776ab?style=for-the-badge&logo=python)](https://python.org)
[![LangChain](https://img.shields.io/badge/LangChain-1.x-00a67e?style=for-the-badge)](https://langchain.com)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ecf8e?style=for-the-badge&logo=supabase)](https://supabase.com)
[![CircleCI](https://img.shields.io/badge/CircleCI-CI%2FCD-343434?style=for-the-badge&logo=circleci)](https://circleci.com)

---

## 📹 Demo

**[▶ Watch full walkthrough on Zight](https://share.zight.com/01a0300c-76db-79a5-a84d-d8e6b21a80ae)**

The demo shows:
- Natural language restaurant search and menu browsing
- Live table booking — confirmed and saved to PostgreSQL
- Food order placement — saved to database + HTML email receipt sent
- Semantic review search (RAG) answering "what do people say about the lamb curry?"
- Booking management — look up and cancel by reference number

---

## 🏗️ Architecture

```
User (natural language)
        ↓
  Streamlit Chat UI
        ↓
  LangChain Agent
  (Gemini 2.0 Flash)
  with 8 tools:
  ├── search_restaurants    → Supabase: restaurants table
  ├── get_menu              → Supabase: menu_items table
  ├── check_availability    → Supabase: time_slots table (real-time)
  ├── make_booking          → Supabase: bookings table (WRITES) + email
  ├── place_order           → Supabase: orders table (WRITES) + email receipt
  ├── check_order           → Supabase: orders table (READ)
  ├── answer_from_reviews   → pgvector: semantic similarity search (RAG)
  └── manage_booking        → Supabase: bookings table (READ/UPDATE)
        ↓
  Resend API → HTML email receipt to customer
```

---

## ✨ Key Features

### 🤖 Agentic AI
- LangChain tool-calling agent with **Gemini 2.0 Flash** as primary LLM
- Agent decides which tool(s) to call based on user intent
- Multi-turn conversation with memory across the session
- Handles ambiguous requests ("book me a table for tonight")

### 🗄️ Real Database Integration
- **Supabase PostgreSQL** — all bookings and orders persist in a real database
- Atomic seat updates via PostgreSQL RPC functions (no race conditions)
- Unique booking references (`OUL-XXXXX`) and order references (`ORD-XXXXX`)
- Real-time availability checking — slot capacity tracked per restaurant per time

### 🔍 Semantic Review Search (RAG)
- 23 real customer reviews embedded using `paraphrase-multilingual-MiniLM-L12-v2`
- **pgvector** similarity search — returns most relevant reviews for any query
- Handles both English and Finnish reviews
- Falls back to keyword search if semantic search fails

### 📧 Email Receipts
- Booking and order confirmations sent as styled HTML emails via **Resend API**
- Professional receipt design with itemised order, total, and delivery details
- Works with any email address — no test/sandbox restrictions

### 🔄 CI/CD Pipeline
- **CircleCI**: runs on every push — unit tests → lint → smoke test
- **GitHub Actions**: weekly slot refresh (Monday 4am) to keep availability current
- 25 unit tests covering database operations, tool logic, and date parsing
- All tests use mocking — no real Supabase connection needed for CI

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| LLM | Gemini 2.0 Flash (primary) / OpenAI GPT-3.5 (fallback) |
| Agent Framework | LangChain 1.x — `bind_tools()` + tool-calling loop |
| Vector Search | pgvector (PostgreSQL extension) |
| Embedding Model | `paraphrase-multilingual-MiniLM-L12-v2` (sentence-transformers) |
| Database | Supabase PostgreSQL (free tier) |
| Email | Resend API (free tier — 100 emails/day) |
| UI | Streamlit |
| CI/CD | CircleCI + GitHub Actions |
| Language | Python 3.11 |

---

## 🗂️ Project Structure

```
oulu-restaurant-chatbot/
├── src/
│   ├── app.py              ← Streamlit chat UI
│   ├── agent.py            ← LangChain agent + 8 tools
│   ├── database.py         ← All Supabase CRUD operations
│   ├── rag.py              ← pgvector semantic search
│   ├── email_sender.py     ← HTML email receipts via Resend
│   └── seed_data.py        ← DB schema + seed data
├── data/
│   └── restaurants.json    ← 5 restaurants + 24 menu items
├── tests/
│   ├── conftest.py
│   ├── test_database.py    ← 15 database unit tests
│   └── test_agent_tools.py ← 10 agent tool tests
├── .circleci/
│   └── config.yml          ← test → lint → smoke test pipeline
└── .github/workflows/
    └── ci.yml              ← weekly slot refresh + PR tests
```

---

## 🚀 Local Setup

### Prerequisites
- Python 3.11
- Free accounts: [Supabase](https://supabase.com) · [Google AI Studio](https://aistudio.google.com) · [Resend](https://resend.com)

### 1. Clone and install

```bash
git clone https://github.com/swat90/oulu-restaurant-chatbot.git
cd oulu-restaurant-chatbot

py -3.11 -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt
```

### 2. Create `.streamlit/secrets.toml`

```toml
SUPABASE_URL  = "https://your-project.supabase.co"
SUPABASE_KEY  = "eyJhbGc..."
GEMINI_API_KEY = "AIza..."
RESEND_API_KEY = "re_..."
EMAIL_FROM    = "onboarding@resend.dev"
```

### 3. Set up Supabase database

- Run the SQL from `src/seed_data.py` → `CREATE_TABLES_SQL` in Supabase SQL Editor
- Enable the `vector` extension in Supabase → Database → Extensions

### 4. Seed the database

```bash
python src/seed_data.py
```

### 5. Run

```bash
streamlit run src/app.py
```

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

All 25 tests use mocking — no real Supabase connection needed.

---

## 💬 Example Conversations

```
User:  "Which restaurant has the best vegetarian options?"
Agent: [calls search_restaurants + answer_from_reviews]
       "Based on customer reviews, Garam Masala and Sauraha are
        highly rated for vegetarian food..."

User:  "I want to order butter chicken and garlic naan for delivery"
Agent: "I'd be happy to place that order! I just need a few details:
        What's your name and email? And what's the delivery address?"
User:  "Anna Test, anna@test.fi, Kirkkokatu 5, Oulu"
Agent: [calls place_order → saves to Supabase → sends email]
       "Order confirmed! 🎉
        Reference: ORD-XK29A
        Butter Chicken: €15.90
        Garlic Naan: €3.50
        Delivery fee: €3.90
        Total: €23.30
        📧 Confirmation sent to anna@test.fi"

User:  "Book a table for 2 at Punjabi Taste on Friday at 7pm"
Agent: [calls check_availability → make_booking → sends email]
       "Table booked! Reference: OUL-AB12C ..."
```

---

## 📄 License

MIT — feel free to use as a portfolio reference or starting point.

---

*Built by [Dr. Swati Garg](https://www.linkedin.com/in/swati-garg-02513153) ·
[Portfolio](https://dr-swati-portfolio.vercel.app) ·
[Google Scholar](https://scholar.google.com/citations?user=xgJjVMYAAAAJ)*
