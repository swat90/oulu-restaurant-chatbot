"""
agent.py - LangChain 1.x tool-calling agent
Uses bind_tools() + manual tool loop — works with Gemini 2.0 Flash
No AgentExecutor, no create_react_agent (removed in LangChain 1.x)
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional
import streamlit as st


def _get_secret(key: str) -> str:
    try:
        return st.secrets.get(key) or ""
    except Exception:
        return os.environ.get(key, "")


def get_llm():
    """Priority: Gemini 2.0 Flash → OpenAI GPT-3.5 → error"""
    gemini_key = _get_secret("GEMINI_API_KEY")
    if gemini_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model="gemini-3.6-flash",
                temperature=0.3,
                google_api_key=gemini_key,
            )
        except Exception as e:
            print(f"Gemini init failed: {e}")

    openai_key = _get_secret("OPENAI_API_KEY")
    if openai_key:
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3, api_key=openai_key)
        except Exception as e:
            print(f"OpenAI init failed: {e}")

    raise ValueError(
        "No LLM configured. Add GEMINI_API_KEY to .streamlit/secrets.toml\n"
        "Get a free key at aistudio.google.com"
    )


from langchain_core.tools import tool
import database as db
import rag


@tool
def search_restaurants(query: str) -> str:
    """Search for restaurants by name, cuisine, or dietary feature (vegan, halal etc).
    Input: plain text search query like 'vegan restaurant' or 'Pakistani food'."""
    restaurants = db.get_all_restaurants()
    q = query.lower()
    matches = [
        r for r in restaurants
        if (q in r["name"].lower()
            or q in r["cuisine"].lower()
            or q in r.get("description", "").lower()
            or any(q in f for f in r.get("features", [])))
    ]
    if not matches:
        matches = restaurants

    lines = []
    for r in matches[:5]:
        lines.append(
            f"{r['name']} ({r['cuisine']})\n"
            f"  Address: {r['address']}\n"
            f"  Price: {r['price_range']} | Rating: {r['rating']}\n"
            f"  Features: {', '.join(r.get('features', []))}\n"
            f"  {r.get('description', '')}"
        )
    return "\n\n".join(lines) if lines else "No restaurants found."


@tool
def get_menu(restaurant_name: str) -> str:
    """Get the full menu for a restaurant including prices and dietary info.
    Input: restaurant name (partial match works, e.g. 'Punjabi')."""
    rest = db.get_restaurant_by_name(restaurant_name)
    if not rest:
        return f"Restaurant '{restaurant_name}' not found."

    items = db.get_menu(rest["id"])
    if not items:
        return f"No menu items found for {rest['name']}."

    by_cat: dict = {}
    for item in items:
        by_cat.setdefault(item["category"], []).append(item)

    lines = [f"Menu for {rest['name']}:"]
    for cat, dishes in by_cat.items():
        lines.append(f"\n{cat}:")
        for d in dishes:
            flags = []
            if d.get("vegetarian"): flags.append("vegetarian")
            if d.get("vegan"):      flags.append("vegan")
            if d.get("gluten_free"):flags.append("gluten-free")
            spice = "chili " * d.get("spice_level", 0)
            lines.append(
                f"  - {d['name']} EUR{d['price']:.2f}"
                + (f" [{', '.join(flags)}]" if flags else "")
                + (f" {spice.strip()}" if spice else "")
                + f"\n    {d.get('description', '')}"
            )
    return "\n".join(lines)


@tool
def check_availability(restaurant_name: str, date: str, party_size: int = 2) -> str:
    """Check table availability at a restaurant.
    Args:
        restaurant_name: name of restaurant (e.g. 'Sauraha')
        date: date string like '2026-06-15', 'tomorrow', or 'Friday'
        party_size: number of guests (default 2)
    """
    date_str   = _parse_date(date)
    party_size = int(party_size)

    if not date_str:
        return "Could not parse date. Use YYYY-MM-DD or 'tomorrow' or a day name like 'Friday'."

    rest = db.get_restaurant_by_name(restaurant_name)
    if not rest:
        return f"Restaurant '{restaurant_name}' not found."

    is_open, hours = db.is_restaurant_open(rest["id"], date_str)
    if not is_open:
        return f"{rest['name']} is closed on {date_str}. Please choose another date."

    slots = db.get_available_slots(rest["id"], date_str, party_size)
    if not slots:
        return f"No available tables for {party_size} people at {rest['name']} on {date_str}."

    times = ", ".join(s["time"] for s in slots)
    return (
        f"{rest['name']} has tables for {party_size} people on {date_str}.\n"
        f"Available times: {times}\n"
        f"Opening hours: {hours}\n"
        f"To book, I need your name, email, and preferred time."
    )


@tool
def make_booking(
    restaurant_name: str,
    date: str,
    time: str,
    party_size: int,
    customer_name: str,
    customer_email: str,
    special_requests: str = "",
) -> str:
    """Create a table reservation.
    Args:
        restaurant_name: name of restaurant
        date: date in YYYY-MM-DD format
        time: time like '19:00'
        party_size: number of guests
        customer_name: full name of customer
        customer_email: email address
        special_requests: any special requests (optional)
    Always collect all required fields before calling this tool.
    """
    rest = db.get_restaurant_by_name(restaurant_name)
    if not rest:
        return f"Restaurant '{restaurant_name}' not found."

    date_str   = str(date)
    time_str   = str(time)
    party_size = int(party_size)

    slots = db.get_available_slots(rest["id"], date_str, party_size)
    slot  = next((s for s in slots if s["time"] == time_str), None)
    if not slot:
        available = ", ".join(s["time"] for s in slots) if slots else "none"
        return f"Time {time_str} not available. Available times: {available}"

    try:
        booking = db.create_booking(
            restaurant_id    = rest["id"],
            slot_id          = slot["slot_id"],
            date_str         = date_str,
            time_str         = time_str,
            party_size       = party_size,
            customer_name    = customer_name,
            customer_email   = customer_email,
            customer_phone   = "",
            special_requests = special_requests,
        )
        ref = booking["booking_ref"]
        return (
            f"Booking confirmed!\n"
            f"Reference: {ref}\n"
            f"Restaurant: {rest['name']}, {rest['address']}\n"
            f"Date: {date_str} at {time_str}\n"
            f"Party of {party_size}\n"
            f"Name: {customer_name} ({customer_email})\n"
            + (f"Special requests: {special_requests}\n" if special_requests else "")
            + f"Save your reference number: {ref}"
        )
    except Exception as e:
        return f"Booking failed: {e}. Please try again."


@tool
def answer_from_reviews(question: str, restaurant_name: str = "") -> str:
    """Answer questions using real customer reviews (semantic search / RAG).
    Use for questions about food quality, service, atmosphere, dish recommendations.
    Args:
        question: the user's question
        restaurant_name: optional — filter to a specific restaurant
    """
    restaurant_id = None
    if restaurant_name:
        rest = db.get_restaurant_by_name(restaurant_name)
        if rest:
            restaurant_id = rest["id"]

    result  = rag.answer_from_reviews(question, restaurant_id)
    context = result["context"]
    n       = result["n_found"]

    if n == 0:
        return "No relevant reviews found."
    return f"Based on {n} customer reviews:\n\n{context}"


@tool
def manage_booking(action: str, booking_ref: str = "", email: str = "") -> str:
    """Look up or cancel an existing booking.
    Args:
        action: 'lookup' or 'cancel'
        booking_ref: booking reference like 'OUL-AB12C' (optional if email given)
        email: customer email to find all bookings (optional if ref given)
    """
    if email and not booking_ref:
        bookings = db.get_bookings_by_email(email)
        if not bookings:
            return f"No active bookings for {email}."
        lines = [f"Found {len(bookings)} booking(s):"]
        for b in bookings:
            rn = (b.get("restaurants", {}).get("name", "")
                  if isinstance(b.get("restaurants"), dict) else "")
            lines.append(
                f"- {b['booking_ref']} at {rn}: {b['date']} {b['time']}, "
                f"party of {b['party_size']}"
            )
        return "\n".join(lines)

    ref = booking_ref.upper()
    if not ref:
        return "Provide a booking reference (e.g. OUL-AB12C) or email."

    booking = db.get_booking_by_ref(ref)
    if not booking:
        return f"No booking found with reference {ref}."

    rn = (booking.get("restaurants", {}).get("name", "")
          if isinstance(booking.get("restaurants"), dict) else "")

    if action == "cancel":
        if db.cancel_booking(ref):
            return f"Booking {ref} cancelled. Restaurant: {rn}, {booking['date']} at {booking['time']}"
        return f"Could not cancel {ref}. It may already be cancelled."

    return (
        f"Booking {ref}\n"
        f"Restaurant: {rn}\n"
        f"Date: {booking['date']} at {booking['time']}\n"
        f"Party of {booking['party_size']}\n"
        f"Name: {booking['customer_name']} ({booking['customer_email']})\n"
        f"Status: {booking['status']}"
        + (f"\nSpecial requests: {booking['special_requests']}"
           if booking.get("special_requests") else "")
    )



@tool
def place_order(
    restaurant_name: str,
    items: str,
    order_type: str,
    customer_name: str,
    customer_email: str,
    delivery_address: str = "",
    notes: str = "",
) -> str:
    """Place a food order (delivery or pickup) at a restaurant.
    Args:
        restaurant_name: name of restaurant
        items: comma-separated list of item names e.g. "Butter Chicken, Garlic Naan"
        order_type: 'delivery' or 'pickup'
        customer_name: customer full name
        customer_email: customer email for receipt
        delivery_address: delivery address (required if order_type is delivery)
        notes: any special instructions
    Always collect customer name, email, items, and order type before calling.
    For delivery, also collect the delivery address.
    """
    rest = db.get_restaurant_by_name(restaurant_name)
    if not rest:
        return f"Restaurant '{restaurant_name}' not found."

    if order_type == "delivery" and not delivery_address:
        return "Please provide a delivery address for delivery orders."

    # Match requested items to menu
    menu_items = db.get_menu(rest["id"])
    menu_by_name = {m["name"].lower(): m for m in menu_items}

    requested = [i.strip() for i in items.split(",")]
    matched_items = []
    not_found = []

    for req in requested:
        req_lower = req.lower()
        # Exact or partial match
        found = None
        for name, item in menu_by_name.items():
            if req_lower in name or name in req_lower:
                found = item
                break
        if found:
            matched_items.append({
                "name":     found["name"],
                "price":    found["price"],
                "quantity": 1,
            })
        else:
            not_found.append(req)

    if not matched_items:
        available = ", ".join(m["name"] for m in menu_items[:8])
        return (
            f"Could not find any of those items on the menu. "
            f"Available items include: {available}"
        )

    warning = ""
    if not_found:
        warning = f"\nNote: Could not find these items: {', '.join(not_found)}"

    try:
        order = db.create_order(
            restaurant_id    = rest["id"],
            customer_name    = customer_name,
            customer_email   = customer_email,
            order_type       = order_type,
            items            = matched_items,
            delivery_address = delivery_address,
            notes            = notes,
        )

        ref      = order["order_ref"]
        subtotal = order["subtotal"]
        total    = order["total"]
        delivery_fee = order["delivery_fee"]
        eta      = order["estimated_time"]

        # Build items summary
        items_text = "\n".join(
            f"  - {i['name']}: €{i['price']:.2f}"
            for i in matched_items
        )

        # Send confirmation email
        email_sent = False
        try:
            from email_sender import send_order_confirmation
            email_sent = send_order_confirmation(
                order_ref        = ref,
                customer_name    = customer_name,
                customer_email   = customer_email,
                restaurant_name  = rest["name"],
                restaurant_address = rest["address"],
                order_type       = order_type,
                delivery_address = delivery_address,
                items            = matched_items,
                subtotal         = subtotal,
                delivery_fee     = delivery_fee,
                total            = total,
                estimated_time   = eta,
            )
        except Exception as e:
            print(f"Email error: {e}")

        email_note = f"\n📧 Confirmation sent to {customer_email}" if email_sent else ""

        return (
            f"Order confirmed! 🎉\n\n"
            f"Order reference: {ref}\n"
            f"Restaurant: {rest['name']}\n"
            f"Type: {order_type.title()}\n"
            + (f"Delivering to: {delivery_address}\n" if order_type == "delivery" else f"Pickup from: {rest['address']}\n")
            + f"Estimated time: {eta}\n\n"
            f"Items:\n{items_text}\n"
            + (f"Delivery fee: €{delivery_fee:.2f}\n" if delivery_fee > 0 else "")
            + f"Total: €{total:.2f}"
            + email_note
            + warning
        )
    except Exception as e:
        return f"Order failed: {e}. Please try again."


@tool
def check_order(order_ref: str = "", email: str = "") -> str:
    """Check the status of an existing order.
    Args:
        order_ref: order reference like 'ORD-AB12C'
        email: customer email to find recent orders
    Provide either order_ref or email.
    """
    if email and not order_ref:
        orders = db.get_orders_by_email(email)
        if not orders:
            return f"No orders found for {email}."
        lines = [f"Recent orders for {email}:"]
        for o in orders:
            rn = (o.get("restaurants", {}).get("name", "")
                  if isinstance(o.get("restaurants"), dict) else "")
            lines.append(
                f"- {o['order_ref']} | {rn} | {o['order_type']} | "
                f"€{o['total']:.2f} | Status: {o['status']}"
            )
        return "\n".join(lines)

    ref = order_ref.upper()
    if not ref:
        return "Please provide an order reference (e.g. ORD-AB12C) or email."

    order = db.get_order_by_ref(ref)
    if not order:
        return f"No order found with reference {ref}."

    rn = (order.get("restaurants", {}).get("name", "")
          if isinstance(order.get("restaurants"), dict) else "")

    items_text = "\n".join(
        f"  - {i['name']}: €{i['price']:.2f}"
        for i in order.get("items", [])
    )

    return (
        f"Order {ref}\n"
        f"Restaurant: {rn}\n"
        f"Type: {order['order_type'].title()}\n"
        f"Status: {order['status'].upper()}\n"
        f"Total: €{order['total']:.2f}\n"
        f"Items:\n{items_text}"
        + (f"\nDelivering to: {order['delivery_address']}" if order.get("delivery_address") else "")
    )


def _parse_date(date_input: str) -> Optional[str]:
    if not date_input:
        return None
    d = date_input.strip().lower()
    today = datetime.now().date()

    if d == "today":
        return today.strftime("%Y-%m-%d")
    if d == "tomorrow":
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")

    day_names = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
    if d in day_names:
        diff = (day_names.index(d) - today.weekday()) % 7
        if diff == 0: diff = 7
        return (today + timedelta(days=diff)).strftime("%Y-%m-%d")

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y", "%d %B %Y", "%B %d %Y"):
        try:
            return datetime.strptime(date_input.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


SYSTEM_PROMPT = (
    "You are a helpful AI assistant for Indian/South Asian restaurants in Oulu, Finland.\n"
    "Help users find restaurants, browse menus, check availability, book tables, and place food orders.\n"
    "Restaurants available: Punjabi Taste, Sauraha, Badipur, Garam Masala, Spice Garden.\n\n"
    "Rules:\n"
    "- Before booking a TABLE, collect: restaurant, date, time, party size, customer name, email.\n"
    "- Before placing an ORDER, collect: restaurant, items wanted, delivery or pickup, customer name, email.\n"
    "  For delivery also collect: delivery address.\n"
    "- For opinion questions use the answer_from_reviews tool.\n"
    "- After booking or ordering, mention that a confirmation email will be sent.\n"
    "- Respond in the user's language (English or Finnish).\n"
    "Today is: {today}\n"
)

TOOLS = [
    search_restaurants,
    get_menu,
    check_availability,
    make_booking,
    place_order,
    check_order,
    answer_from_reviews,
    manage_booking,
]


def chat(user_message: str, history: list) -> str:
    """
    Send message through LangChain 1.x tool-calling loop.
    Uses bind_tools() — works with Gemini and OpenAI.
    """
    from langchain_core.messages import (
        HumanMessage, AIMessage, SystemMessage, ToolMessage
    )
    import warnings
    warnings.filterwarnings("ignore")

    tools_by_name = {t.name: t for t in TOOLS}
    llm_with_tools = get_llm().bind_tools(TOOLS)
    today_str      = datetime.now().strftime("%A, %d %B %Y")

    # Build message list
    messages = [SystemMessage(content=SYSTEM_PROMPT.format(today=today_str))]

    for msg in history[:-1]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))

    messages.append(HumanMessage(content=user_message))

    # Tool-calling loop — max 6 iterations
    for iteration in range(6):
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        # Check for tool calls
        tool_calls = getattr(response, "tool_calls", None)
        if not tool_calls:
            # No tool calls = final answer
            content = response.content
            if isinstance(content, list):
                # Gemini sometimes returns list of content blocks
                content = " ".join(
                    c.get("text", "") if isinstance(c, dict) else str(c)
                    for c in content
                )
            return content or "I could not generate a response. Please try again."

        # Execute each tool call
        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_id   = tool_call.get("id", tool_name)

            if tool_name in tools_by_name:
                try:
                    result = tools_by_name[tool_name].invoke(tool_args)
                except Exception as e:
                    result = f"Tool error: {str(e)}"
            else:
                result = f"Unknown tool: {tool_name}"

            messages.append(
                ToolMessage(content=str(result), tool_call_id=tool_id)
            )

    return "I reached the maximum steps. Please try a simpler question."
