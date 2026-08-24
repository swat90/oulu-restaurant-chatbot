# Setup Guide — Step by Step

## Step 1: Supabase (10 minutes)

1. Go to supabase.com → New project → name it "oulu-chatbot"
2. Wait for it to provision (~2 min)
3. Go to **Settings → API** → copy:
   - `Project URL` → this is your `SUPABASE_URL`
   - `anon public` key → this is your `SUPABASE_KEY`
4. Go to **SQL Editor** → paste and run the SQL from `src/seed_data.py`
   (the big block at the top of the file between the triple quotes)

## Step 2: Local setup

```bash
# Create project folder
mkdir oulu-restaurant-chatbot
cd oulu-restaurant-chatbot

# Copy all files here, then:
py -3.11 -m venv venv
venv\Scripts\activate

pip install -r requirements.txt

# Create .env file
copy .env.example .env
# Open .env and fill in SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY
```

## Step 3: Seed the database

```bash
python src/seed_data.py
```

This will:
- Ask you to confirm you've run the SQL (press Enter)
- Insert 5 restaurants + menus
- Generate time slots for 30 days
- Insert 23 sample reviews
- Embed all reviews for RAG (takes ~2 min, downloads model first time)

## Step 4: Run locally

```bash
streamlit run src/app.py
# Opens at http://localhost:8501
```

Test it works by trying:
- "Show me the menu for Punjabi Taste"
- "Is Sauraha open on Sunday?"
- "Book a table for 2 at Garam Masala on Friday at 7pm"
- "What do people say about the lamb curry?"

## Step 5: Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit — Oulu restaurant chatbot"
git remote add origin https://github.com/YOUR_USERNAME/oulu-restaurant-chatbot.git
git branch -M main
git push -u origin main
```

Make sure `.env` and `venv/` are in `.gitignore` — they are by default.

## Step 6: Streamlit Cloud

1. Go to share.streamlit.io → New app
2. Repository: your GitHub repo
3. Main file: `src/app.py`
4. Click **Advanced settings** → add secrets:

```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-anon-key"
OPENAI_API_KEY = "sk-..."
```

5. Deploy → get URL like `oulu-restaurant-chatbot.streamlit.app`

## Step 7: CircleCI

1. Go to app.circleci.com → sign in with GitHub
2. Click **Set Up Project** → select your repo
3. It will find `.circleci/config.yml` automatically
4. Go to **Project Settings → Environment Variables** → add:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `STREAMLIT_APP_URL` (your Streamlit URL from Step 6)

Now every `git push` triggers: tests → lint → smoke test.
You'll see a green ✅ or red ❌ badge on your GitHub repo.

## Step 8: Add CircleCI badge to README

In `README.md`, add this line at the top:
```
[![CircleCI](https://dl.circleci.com/status-badge/img/gh/YOUR_USERNAME/oulu-restaurant-chatbot/tree/main.svg?style=svg)](https://dl.circleci.com/status-badge/redirect/gh/YOUR_USERNAME/oulu-restaurant-chatbot/tree/main)
```

Replace `YOUR_USERNAME` with your GitHub username.
This shows a live passing/failing badge — impressive on a portfolio.

## Step 9: Add to portfolio

In `Work.jsx`, add a new item to Production Systems tab:

```javascript
{
  tab: 'Production Systems',
  icon: '🍽️',
  badge: 'Live · Supabase',
  badgeColor: 'green',
  title: 'Oulu Restaurant Booking Chatbot',
  subtitle: 'LangChain · Supabase · pgvector · CircleCI',
  description: 'Agentic AI chatbot...',
  demo: 'https://oulu-restaurant-chatbot.streamlit.app',
  demoLabel: 'Open Chatbot ↗',
}
```

## Troubleshooting

**"Missing SUPABASE_URL"** → check .env file exists and has correct values

**"No LLM configured"** → add OPENAI_API_KEY or HF_TOKEN to .env

**Tests failing locally** → make sure you're in the venv:
`venv\Scripts\activate`

**Streamlit app goes to sleep** → free tier sleeps after 7 days inactivity.
Add a note in your portfolio: "Click to wake if loading..."
