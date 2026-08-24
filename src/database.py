"""
database.py
────────────
Supabase connection + all database operations.
Uses Supabase Python client — no credentials in code,
reads from environment variables / Streamlit secrets.

Tables:
  restaurants   — place info, hours, capacity
  menu_items    — dishes per restaurant
  bookings      — reservations (created by chatbot)
  reviews       — review text + embeddings for RAG
  time_slots    — available booking slots per restaurant per day
"""

import os
import json
from datetime import datetime, date, timedelta
from typing import Optional
import streamlit as st

# ── Supabase client ───────────────────────────────────────────────────────────
_supabase_client = None   # module-level cache for non-Streamlit contexts

def get_supabase():
    """
    Lazy-load Supabase client.
    Uses Streamlit cache when running in Streamlit,
    falls back to module-level singleton when running as plain Python script.
    """
    global _supabase_client
    from supabase import create_client

    # Try Streamlit secrets first (when running via streamlit)
    url, key = "", ""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except Exception:
        pass

    # Fall back to environment variables (when running as plain script)
    if not url:
        url = os.environ.get("SUPABASE_URL", "")
    if not key:
        key = os.environ.get("SUPABASE_KEY", "")

    if not url or not key:
        raise ValueError(
            "Missing SUPABASE_URL or SUPABASE_KEY.\n"
            "Set them in your .env file or Streamlit secrets.\n"
            "SUPABASE_KEY should be the long JWT anon key starting with eyJ..."
        )

    # Reuse existing client if already created
    if _supabase_client is not None:
        return _supabase_client

    _supabase_client = create_client(url, key)
    return _supabase_client

# ── Restaurant queries ────────────────────────────────────────────────────────

def get_all_restaurants() -> list[dict]:
    """Return all restaurants with basic info."""
    sb = get_supabase()
    resp = sb.table("restaurants").select("*").execute()
    return resp.data or []


def get_restaurant_by_name(name: str) -> Optional[dict]:
    """Fuzzy match restaurant by name (case-insensitive contains)."""
    sb = get_supabase()
    resp = (
        sb.table("restaurants")
        .select("*")
        .ilike("name", f"%{name}%")
        .limit(1)
        .execute()
    )
    return resp.data[0] if resp.data else None


def get_restaurant_by_id(restaurant_id: int) -> Optional[dict]:
    sb = get_supabase()
    resp = (
        sb.table("restaurants")
        .select("*")
        .eq("id", restaurant_id)
        .single()
        .execute()
    )
    return resp.data


def get_restaurants_by_feature(feature: str) -> list[dict]:
    """
    Find restaurants that have a specific feature.
    Features: 'vegan', 'vegetarian', 'halal', 'gluten-free',
              'takeaway', 'delivery', 'lunch buffet', 'wine'
    """
    sb = get_supabase()
    resp = (
        sb.table("restaurants")
        .select("*")
        .contains("features", [feature])
        .execute()
    )
    return resp.data or []

# ── Menu queries ──────────────────────────────────────────────────────────────

def get_menu(restaurant_id: int) -> list[dict]:
    """Get full menu for a restaurant."""
    sb = get_supabase()
    resp = (
        sb.table("menu_items")
        .select("*")
        .eq("restaurant_id", restaurant_id)
        .order("category")
        .execute()
    )
    return resp.data or []


def search_menu_items(
    query: str,
    vegetarian: bool = False,
    vegan: bool = False,
    gluten_free: bool = False,
    max_spice: int = 5,
    restaurant_id: Optional[int] = None,
) -> list[dict]:
    """Search menu items with dietary filters."""
    sb = get_supabase()
    q = (
        sb.table("menu_items")
        .select("*, restaurants(name)")
        .ilike("name", f"%{query}%")
        .lte("spice_level", max_spice)
    )
    if vegetarian:
        q = q.eq("vegetarian", True)
    if vegan:
        q = q.eq("vegan", True)
    if gluten_free:
        q = q.eq("gluten_free", True)
    if restaurant_id:
        q = q.eq("restaurant_id", restaurant_id)

    resp = q.execute()
    return resp.data or []

# ── Availability ──────────────────────────────────────────────────────────────

def get_available_slots(
    restaurant_id: int,
    date_str: str,       # YYYY-MM-DD
    party_size: int = 2,
) -> list[dict]:
    """
    Return available time slots for a restaurant on a given date.
    A slot is available if:
      - it exists in time_slots table
      - booked_seats + party_size <= slot capacity
    """
    sb = get_supabase()
    resp = (
        sb.table("time_slots")
        .select("*")
        .eq("restaurant_id", restaurant_id)
        .eq("date", date_str)
        .execute()
    )
    slots = resp.data or []

    available = []
    for slot in slots:
        remaining = slot["capacity"] - slot["booked_seats"]
        if remaining >= party_size:
            available.append({
                "slot_id":   slot["id"],
                "time":      slot["time"],
                "remaining": remaining,
            })
    return available


def is_restaurant_open(restaurant_id: int, date_str: str) -> tuple[bool, str]:
    """Check if restaurant is open on a given date. Returns (is_open, hours)."""
    rest = get_restaurant_by_id(restaurant_id)
    if not rest:
        return False, "Restaurant not found"

    target = datetime.strptime(date_str, "%Y-%m-%d").date()
    day_name = target.strftime("%A").lower()

    hours = rest.get("opening_hours", {}).get(day_name, "closed")
    if hours == "closed":
        return False, "closed"
    return True, hours

# ── Bookings ──────────────────────────────────────────────────────────────────

def create_booking(
    restaurant_id: int,
    slot_id: int,
    date_str: str,
    time_str: str,
    party_size: int,
    customer_name: str,
    customer_email: str,
    customer_phone: str = "",
    special_requests: str = "",
) -> dict:
    """
    Create a booking and update the slot's booked_seats.
    Returns the created booking record.
    """
    sb = get_supabase()

    # 1. Create booking record
    booking_data = {
        "restaurant_id":    restaurant_id,
        "slot_id":          slot_id,
        "date":             date_str,
        "time":             time_str,
        "party_size":       party_size,
        "customer_name":    customer_name,
        "customer_email":   customer_email,
        "customer_phone":   customer_phone,
        "special_requests": special_requests,
        "status":           "confirmed",
        "created_at":       datetime.utcnow().isoformat(),
        "booking_ref":      _generate_booking_ref(),
    }

    booking_resp = sb.table("bookings").insert(booking_data).execute()

    if not booking_resp.data:
        raise ValueError("Failed to create booking")

    booking = booking_resp.data[0]

    # 2. Update slot booked_seats
    sb.rpc("increment_booked_seats", {
        "p_slot_id":    slot_id,
        "p_party_size": party_size,
    }).execute()

    return booking


def get_booking_by_ref(booking_ref: str) -> Optional[dict]:
    """Look up a booking by reference number."""
    sb = get_supabase()
    resp = (
        sb.table("bookings")
        .select("*, restaurants(name, address, phone)")
        .eq("booking_ref", booking_ref)
        .single()
        .execute()
    )
    return resp.data


def cancel_booking(booking_ref: str) -> bool:
    """Cancel a booking and free the slot."""
    sb = get_supabase()

    # Get booking first
    booking = get_booking_by_ref(booking_ref)
    if not booking or booking["status"] == "cancelled":
        return False

    # Update status
    sb.table("bookings").update({"status": "cancelled"}).eq(
        "booking_ref", booking_ref
    ).execute()

    # Free the slot
    sb.rpc("decrement_booked_seats", {
        "p_slot_id":    booking["slot_id"],
        "p_party_size": booking["party_size"],
    }).execute()

    return True


def get_bookings_by_email(email: str) -> list[dict]:
    """Get all bookings for a customer email."""
    sb = get_supabase()
    resp = (
        sb.table("bookings")
        .select("*, restaurants(name, address)")
        .eq("customer_email", email)
        .eq("status", "confirmed")
        .order("date")
        .execute()
    )
    return resp.data or []

# ── Review search (for RAG) ───────────────────────────────────────────────────

def get_reviews_for_restaurant(
    restaurant_id: int,
    limit: int = 20,
) -> list[dict]:
    """Get recent reviews for a restaurant."""
    sb = get_supabase()
    resp = (
        sb.table("reviews")
        .select("text_translated, stars, visited_in, ctx_recommended")
        .eq("restaurant_id", restaurant_id)
        .order("stars", desc=True)
        .limit(limit)
        .execute()
    )
    return resp.data or []


def search_reviews_semantic(
    query_embedding: list[float],
    restaurant_id: Optional[int] = None,
    limit: int = 5,
) -> list[dict]:
    """
    Vector similarity search over review embeddings using pgvector.
    Returns most relevant reviews for the query.
    """
    sb = get_supabase()
    params = {
        "query_embedding": query_embedding,
        "match_count":     limit,
    }
    if restaurant_id:
        params["filter_restaurant_id"] = restaurant_id

    resp = sb.rpc("match_reviews", params).execute()
    return resp.data or []

# ── Helpers ───────────────────────────────────────────────────────────────────

def _generate_booking_ref() -> str:
    """Generate a short human-readable booking reference."""
    import random, string
    prefix = "OUL"
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"{prefix}-{suffix}"


def seed_time_slots(restaurant_id: int, days_ahead: int = 30):
    """
    Populate time_slots for the next N days for a restaurant.
    Call this from seed_data.py — not during normal operation.
    """
    sb = get_supabase()
    rest = get_restaurant_by_id(restaurant_id)
    if not rest:
        return

    slots_to_insert = []
    base = date.today()
    standard_times = ["12:00", "13:00", "14:00", "17:00", "18:00",
                      "19:00", "20:00", "21:00"]

    for i in range(1, days_ahead + 1):
        target = base + timedelta(days=i)
        date_str = target.strftime("%Y-%m-%d")
        day_name = target.strftime("%A").lower()
        hours = rest["opening_hours"].get(day_name, "closed")
        if not hours or hours.lower() == "closed":
            continue

        # Handle multiple dash types: en-dash (–), em-dash (—), hyphen (-)
        # and possible whitespace around them
        import re
        parts = re.split(r'[–—-]', hours)
        if len(parts) < 2:
            continue  # unrecognised format, skip
        try:
            open_h  = int(parts[0].strip().split(":")[0])
            close_h = int(parts[1].strip().split(":")[0])
        except (ValueError, IndexError):
            continue  # skip malformed hours

        for t in standard_times:
            slot_h = int(t.split(":")[0])
            if open_h <= slot_h < close_h - 1:
                slots_to_insert.append({
                    "restaurant_id": restaurant_id,
                    "date":          date_str,
                    "time":          t,
                    "capacity":      rest["capacity"] // 4,  # seats per slot
                    "booked_seats":  0,
                })

    if slots_to_insert:
        sb.table("time_slots").insert(slots_to_insert).execute()
        print(f"  Inserted {len(slots_to_insert)} slots for restaurant {restaurant_id}")


# ── Orders ────────────────────────────────────────────────────────────────────

def create_order(
    restaurant_id: int,
    customer_name: str,
    customer_email: str,
    order_type: str,
    items: list,
    delivery_address: str = "",
    customer_phone: str = "",
    notes: str = "",
) -> dict:
    """
    Create an order and save to Supabase.
    items: list of {"name": str, "price": float, "quantity": int}
    Returns the created order record.
    """
    sb = get_supabase()

    subtotal     = sum(i["price"] * i.get("quantity", 1) for i in items)
    delivery_fee = 3.90 if order_type == "delivery" else 0.0
    total        = round(subtotal + delivery_fee, 2)
    estimated    = "30-45 min" if order_type == "delivery" else "15-20 min"

    order_data = {
        "order_ref":        _generate_order_ref(),
        "restaurant_id":    restaurant_id,
        "customer_name":    customer_name,
        "customer_email":   customer_email,
        "customer_phone":   customer_phone,
        "order_type":       order_type,
        "delivery_address": delivery_address,
        "items":            items,
        "subtotal":         subtotal,
        "delivery_fee":     delivery_fee,
        "total":            total,
        "estimated_time":   estimated,
        "notes":            notes,
        "status":           "confirmed",
        "created_at":       datetime.utcnow().isoformat(),
    }

    resp = sb.table("orders").insert(order_data).execute()
    if not resp.data:
        raise ValueError("Failed to create order")
    return resp.data[0]


def get_order_by_ref(order_ref: str) -> dict:
    """Look up an order by reference number."""
    sb   = get_supabase()
    resp = (
        sb.table("orders")
        .select("*, restaurants(name, address, phone)")
        .eq("order_ref", order_ref)
        .single()
        .execute()
    )
    return resp.data


def get_orders_by_email(email: str) -> list:
    """Get all orders for a customer email."""
    sb   = get_supabase()
    resp = (
        sb.table("orders")
        .select("*, restaurants(name)")
        .eq("customer_email", email)
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )
    return resp.data or []


def _generate_order_ref() -> str:
    import random, string
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"ORD-{suffix}"
