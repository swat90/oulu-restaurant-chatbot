"""
seed_data.py
─────────────
Run this ONCE to populate your Supabase database.
Creates all tables, inserts restaurants, menus, sample reviews,
and generates time slots for the next 30 days.

Run: python src/seed_data.py
"""

import os, json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))

# ── Load env before importing database ───────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

import database as db

DATA_FILE = pathlib.Path(__file__).parent.parent / "data" / "restaurants.json"

# ── SQL to create tables (run via Supabase SQL editor) ───────────────────────
CREATE_TABLES_SQL = """
-- Enable pgvector extension (run once in Supabase SQL editor)
CREATE EXTENSION IF NOT EXISTS vector;

-- Restaurants
CREATE TABLE IF NOT EXISTS restaurants (
  id             SERIAL PRIMARY KEY,
  name           TEXT NOT NULL,
  cuisine        TEXT,
  address        TEXT,
  phone          TEXT,
  email          TEXT,
  price_range    TEXT,
  rating         FLOAT,
  opening_hours  JSONB,
  capacity       INTEGER,
  features       TEXT[],
  description    TEXT,
  created_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Menu items
CREATE TABLE IF NOT EXISTS menu_items (
  id            SERIAL PRIMARY KEY,
  restaurant_id INTEGER REFERENCES restaurants(id) ON DELETE CASCADE,
  category      TEXT,
  name          TEXT NOT NULL,
  price         FLOAT,
  vegetarian    BOOLEAN DEFAULT FALSE,
  vegan         BOOLEAN DEFAULT FALSE,
  gluten_free   BOOLEAN DEFAULT FALSE,
  spice_level   INTEGER DEFAULT 0 CHECK (spice_level BETWEEN 0 AND 5),
  description   TEXT
);

-- Time slots for bookings
CREATE TABLE IF NOT EXISTS time_slots (
  id            SERIAL PRIMARY KEY,
  restaurant_id INTEGER REFERENCES restaurants(id) ON DELETE CASCADE,
  date          DATE NOT NULL,
  time          TIME NOT NULL,
  capacity      INTEGER NOT NULL,
  booked_seats  INTEGER DEFAULT 0,
  UNIQUE(restaurant_id, date, time)
);

-- Bookings
CREATE TABLE IF NOT EXISTS bookings (
  id               SERIAL PRIMARY KEY,
  restaurant_id    INTEGER REFERENCES restaurants(id),
  slot_id          INTEGER REFERENCES time_slots(id),
  date             DATE NOT NULL,
  time             TIME NOT NULL,
  party_size       INTEGER NOT NULL,
  customer_name    TEXT NOT NULL,
  customer_email   TEXT NOT NULL,
  customer_phone   TEXT,
  special_requests TEXT,
  status           TEXT DEFAULT 'confirmed'
                   CHECK (status IN ('confirmed','cancelled','completed')),
  booking_ref      TEXT UNIQUE NOT NULL,
  created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- Reviews with vector embedding for RAG
CREATE TABLE IF NOT EXISTS reviews (
  id               SERIAL PRIMARY KEY,
  restaurant_id    INTEGER REFERENCES restaurants(id),
  reviewer_name    TEXT,
  stars            FLOAT,
  text             TEXT,
  text_translated  TEXT,
  language         TEXT DEFAULT 'en',
  visited_in       TEXT,
  ctx_recommended  TEXT,
  embedding        vector(384),   -- paraphrase-multilingual-MiniLM-L12-v2 dimension
  created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast vector similarity search
CREATE INDEX IF NOT EXISTS reviews_embedding_idx
  ON reviews USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 50);

-- RPC functions for atomic seat updates
CREATE OR REPLACE FUNCTION increment_booked_seats(
  p_slot_id    INTEGER,
  p_party_size INTEGER
) RETURNS void AS $$
  UPDATE time_slots
  SET booked_seats = booked_seats + p_party_size
  WHERE id = p_slot_id;
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION decrement_booked_seats(
  p_slot_id    INTEGER,
  p_party_size INTEGER
) RETURNS void AS $$
  UPDATE time_slots
  SET booked_seats = GREATEST(0, booked_seats - p_party_size)
  WHERE id = p_slot_id;
$$ LANGUAGE sql;

-- RPC function for vector similarity search
CREATE OR REPLACE FUNCTION match_reviews(
  query_embedding       vector(384),
  match_count           INTEGER DEFAULT 5,
  filter_restaurant_id  INTEGER DEFAULT NULL
) RETURNS TABLE (
  id               INTEGER,
  restaurant_id    INTEGER,
  stars            FLOAT,
  text_translated  TEXT,
  ctx_recommended  TEXT,
  similarity       FLOAT
) AS $$
  SELECT
    r.id,
    r.restaurant_id,
    r.stars,
    r.text_translated,
    r.ctx_recommended,
    1 - (r.embedding <=> query_embedding) AS similarity
  FROM reviews r
  WHERE
    r.embedding IS NOT NULL
    AND (filter_restaurant_id IS NULL OR r.restaurant_id = filter_restaurant_id)
  ORDER BY r.embedding <=> query_embedding
  LIMIT match_count;
$$ LANGUAGE sql;
"""

# ── Sample reviews ─────────────────────────────────────────────────────────────
SAMPLE_REVIEWS = [
    # Punjabi Taste
    {"restaurant_id": 1, "reviewer_name": "Maria K",    "stars": 5, "language": "en", "text_translated": "Amazing butter chicken, best I've had in Oulu! The naan was perfectly fluffy and the staff were so friendly. Definitely coming back.", "ctx_recommended": "butter chicken, garlic naan"},
    {"restaurant_id": 1, "reviewer_name": "Juha L",     "stars": 5, "language": "fi", "text_translated": "Really good and tasty food. Lamb rogan josh was outstanding. Mango lassi was delicious. Very clean restaurant.", "ctx_recommended": "lamb rogan josh, mango lassi"},
    {"restaurant_id": 1, "reviewer_name": "Anna S",     "stars": 4, "language": "en", "text_translated": "Great vegetarian options! Palak paneer was creamy and fresh. Service was a bit slow but worth the wait.", "ctx_recommended": "palak paneer, dal makhani"},
    {"restaurant_id": 1, "reviewer_name": "Mikko P",    "stars": 5, "language": "fi", "text_translated": "Excellent food and friendly service. The spice levels were perfect — not too hot, not too mild. Great lunch spot.", "ctx_recommended": "chicken tikka, garlic naan"},
    {"restaurant_id": 1, "reviewer_name": "Hanan A",    "stars": 5, "language": "en", "text_translated": "Perfect environment, friendly staff, and tasty food. The paneer butter masala was incredible. Clean and comfortable.", "ctx_recommended": "paneer butter masala"},
    {"restaurant_id": 1, "reviewer_name": "Tuuli T",    "stars": 4, "language": "en", "text_translated": "Good vegetarian options including palak paneer. No music which was pleasant. Beautiful and clean restaurant. Staff very friendly.", "ctx_recommended": "palak paneer, samosa"},
    {"restaurant_id": 1, "reviewer_name": "minni h",    "stars": 5, "language": "fi", "text_translated": "Really tasty and good sized portions. The lentil soup as a starter was irresistible! Kids loved the chicken. Mango lassi for dessert crowned the meal.", "ctx_recommended": "lentil soup, chicken tikka, mango lassi"},

    # Sauraha
    {"restaurant_id": 2, "reviewer_name": "Erika V",    "stars": 5, "language": "en", "text_translated": "The momos here are incredible — crispy outside, juicy inside. Lunch buffet is great value at €12.90. Dal bhat is authentic and filling.", "ctx_recommended": "momos, dal bhat, lunch buffet"},
    {"restaurant_id": 2, "reviewer_name": "Petri M",    "stars": 4, "language": "fi", "text_translated": "Good Nepali food. The chicken curry was very spicy and flavorful. Lunch buffet has lots of variety. Service could be faster.", "ctx_recommended": "chicken curry, lunch buffet"},
    {"restaurant_id": 2, "reviewer_name": "Sarah L",    "stars": 5, "language": "en", "text_translated": "Best momos in Oulu hands down! Excellent vegan options too. The atmosphere is calm and welcoming.", "ctx_recommended": "veg momos, dal bhat"},
    {"restaurant_id": 2, "reviewer_name": "Tapio N",    "stars": 3, "language": "fi", "text_translated": "Average food, nothing special. The buffet was okay but some dishes were lukewarm. Service was friendly though.", "ctx_recommended": "lunch buffet"},
    {"restaurant_id": 2, "reviewer_name": "Emma R",     "stars": 5, "language": "en", "text_translated": "Wonderful family restaurant. Kids loved the mild chicken dishes. Very accommodating with dietary requirements.", "ctx_recommended": "chicken momos, dal bhat"},

    # Badipur
    {"restaurant_id": 3, "reviewer_name": "Karim H",    "stars": 4, "language": "en", "text_translated": "Authentic Bangladeshi fish curry — exactly like back home. Good spice levels. Cheap lunch specials.", "ctx_recommended": "fish curry, chicken tikka masala"},
    {"restaurant_id": 3, "reviewer_name": "Lisa O",     "stars": 4, "language": "fi", "text_translated": "Good Indian food for the price. Chana masala was tasty and filling. Small restaurant but cozy atmosphere.", "ctx_recommended": "chana masala"},
    {"restaurant_id": 3, "reviewer_name": "David W",    "stars": 3, "language": "en", "text_translated": "Decent food but nothing remarkable. Fish curry was good, service was a bit slow. Will try again.", "ctx_recommended": "fish curry"},

    # Garam Masala
    {"restaurant_id": 4, "reviewer_name": "Sophie K",   "stars": 5, "language": "en", "text_translated": "Finally proper South Indian food in Oulu! The masala dosa was crispy and perfectly made. Sambar was excellent. Great wine selection too.", "ctx_recommended": "masala dosa, sambar"},
    {"restaurant_id": 4, "reviewer_name": "Aleksi J",   "stars": 5, "language": "fi", "text_translated": "Best Indian restaurant in Oulu. Lamb vindaloo was extremely spicy but amazing. Gulab jamun for dessert was perfect.", "ctx_recommended": "lamb vindaloo, gulab jamun"},
    {"restaurant_id": 4, "reviewer_name": "Priya M",    "stars": 5, "language": "en", "text_translated": "Authentic South Indian cuisine. The idli and dosa are made traditionally. Paneer tikka masala was also excellent.", "ctx_recommended": "masala dosa, paneer tikka masala"},
    {"restaurant_id": 4, "reviewer_name": "Thomas B",   "stars": 4, "language": "en", "text_translated": "Good food, romantic atmosphere for a date night. Closed on Mondays which is inconvenient. But worth visiting.", "ctx_recommended": "lamb vindaloo, gulab jamun"},

    # Spice Garden
    {"restaurant_id": 5, "reviewer_name": "Nina V",     "stars": 4, "language": "en", "text_translated": "Great vegan options! The vegan thali was a feast — 5 different dishes all delicious. Wolt delivery also works well.", "ctx_recommended": "vegan thali, kottu roti"},
    {"restaurant_id": 5, "reviewer_name": "Hassan A",   "stars": 5, "language": "en", "text_translated": "Best prawn curry I've had outside Sri Lanka. Kottu roti is a must-try. Staff are very welcoming.", "ctx_recommended": "prawn curry, kottu roti"},
    {"restaurant_id": 5, "reviewer_name": "Riikka P",   "stars": 4, "language": "fi", "text_translated": "Good Sri Lankan food. Onion bhaji as starter was crispy and tasty. Prawn curry had great flavor. Will visit again.", "ctx_recommended": "onion bhaji, prawn curry"},
    {"restaurant_id": 5, "reviewer_name": "Omar S",     "stars": 3, "language": "en", "text_translated": "Average experience. Food was okay, not outstanding. Service was slow during lunch hour. The kottu roti was the highlight.", "ctx_recommended": "kottu roti"},
]

# ── Main seed function ─────────────────────────────────────────────────────────

def seed():
    print("="*60)
    print("SEED DATA — Oulu Restaurant Chatbot")
    print("="*60)
    print()
    print("STEP 0: Run the SQL below in your Supabase SQL editor first!")
    print("-"*60)
    print(CREATE_TABLES_SQL)
    print("-"*60)
    input("\nPress Enter once you've run the SQL in Supabase... ")

    sb = db.get_supabase()

    # ── Restaurants ──────────────────────────────────────────────────────────
    print("\n1. Inserting restaurants...")
    with open(DATA_FILE) as f:
        data = json.load(f)

    for rest in data["restaurants"]:
        # Check if already exists
        existing = sb.table("restaurants").select("id").eq("id", rest["id"]).execute()
        if existing.data:
            print(f"  Skipping {rest['name']} (already exists)")
            continue
        sb.table("restaurants").insert(rest).execute()
        print(f"  Inserted: {rest['name']}")

    # ── Menu items ────────────────────────────────────────────────────────────
    print("\n2. Inserting menu items...")
    for item in data["menu_items"]:
        existing = sb.table("menu_items").select("id").eq("id", item["id"]).execute()
        if existing.data:
            continue
        sb.table("menu_items").insert(item).execute()
    print(f"  Inserted {len(data['menu_items'])} menu items")

    # ── Time slots ────────────────────────────────────────────────────────────
    print("\n3. Generating time slots (next 30 days)...")
    for rest in data["restaurants"]:
        db.seed_time_slots(rest["id"], days_ahead=30)

    # ── Reviews ───────────────────────────────────────────────────────────────
    print("\n4. Inserting sample reviews...")
    for review in SAMPLE_REVIEWS:
        sb.table("reviews").insert(review).execute()
    print(f"  Inserted {len(SAMPLE_REVIEWS)} reviews")

    # ── Embed reviews ─────────────────────────────────────────────────────────
    print("\n5. Generating review embeddings (for RAG)...")
    from rag import embed_and_store_reviews
    embed_and_store_reviews()

    print("\n✅ Database seeded successfully!")
    print("You can now run: streamlit run src/app.py")

if __name__ == "__main__":
    seed()

# ── Orders table SQL (add to Supabase SQL editor) ─────────────────────────────
ORDERS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS orders (
  id             SERIAL PRIMARY KEY,
  order_ref      TEXT UNIQUE NOT NULL,
  restaurant_id  INTEGER REFERENCES restaurants(id),
  customer_name  TEXT NOT NULL,
  customer_email TEXT NOT NULL,
  customer_phone TEXT,
  order_type     TEXT DEFAULT 'delivery' CHECK (order_type IN ('delivery','pickup')),
  delivery_address TEXT,
  items          JSONB NOT NULL,
  subtotal       FLOAT NOT NULL,
  delivery_fee   FLOAT DEFAULT 3.90,
  total          FLOAT NOT NULL,
  status         TEXT DEFAULT 'confirmed'
                 CHECK (status IN ('confirmed','preparing','delivered','picked_up','cancelled')),
  estimated_time TEXT,
  notes          TEXT,
  created_at     TIMESTAMPTZ DEFAULT NOW()
);
"""
