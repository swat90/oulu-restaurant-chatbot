# Oulu Restaurant AI Chatbot

Agentic AI chatbot for finding and booking tables at Indian/South Asian
restaurants in Oulu, Finland. Demonstrates:

- **LangChain agent** with 6 tools (search, menu, availability, booking, RAG, manage)
- **Supabase PostgreSQL** for live booking storage
- **pgvector** for semantic review search (RAG)
- **CircleCI** for automated testing on every push
- **GitHub Actions** for weekly time slot refresh

## Live Demo
👉 [Open Chatbot](https://oulu-restaurant-chatbot.streamlit.app)

## Setup

### 1. Supabase
- Create free account at supabase.com
- Copy `SUPABASE_URL` and `SUPABASE_KEY` (anon key) from project settings
- Run the SQL from `src/seed_data.py` in the Supabase SQL editor

### 2. Environment
```bash
cp .env.example .env
# Fill in your values
```

### 3. Install & seed
```bash
py -3.11 -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python src/seed_data.py      # Run once to populate DB
```

### 4. Run locally
```bash
streamlit run src/app.py
```

### 5. Deploy to Streamlit Cloud
- Push to GitHub
- Connect at share.streamlit.io
- Add secrets: SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY

### 6. CircleCI
- Connect repo at app.circleci.com
- Add env vars: SUPABASE_URL, SUPABASE_KEY, STREAMLIT_APP_URL
- Every push triggers: test → lint → smoke test

## Architecture
```
User → Streamlit chat UI
         ↓
    LangChain Agent (GPT-3.5 / Mistral)
    ├── search_restaurants   → Supabase restaurants table
    ├── get_menu             → Supabase menu_items table
    ├── check_availability   → Supabase time_slots table
    ├── make_booking         → Supabase bookings table (WRITES)
    ├── answer_from_reviews  → pgvector similarity search
    └── manage_booking       → Supabase bookings table (READ/UPDATE)
```

## CI/CD
```
git push
    ├── CircleCI: test → lint → smoke_test (every push)
    └── GitHub Actions: refresh time slots (every Monday)
```
