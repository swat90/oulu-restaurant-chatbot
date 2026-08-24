"""
email_sender.py
────────────────
Sends order confirmation and booking confirmation emails.
Uses Resend (resend.com) — 100 emails/day free, no credit card.

Setup:
1. Go to resend.com → sign up free
2. Get API key from dashboard
3. Add to .streamlit/secrets.toml:
   RESEND_API_KEY = "re_..."
   EMAIL_FROM = "onboarding@resend.dev"  (use this for testing — no domain needed)
"""

import os
import streamlit as st
from datetime import datetime


def _get_secret(key: str) -> str:
    try:
        return st.secrets.get(key) or ""
    except Exception:
        return os.environ.get(key, "")


def send_order_confirmation(
    order_ref: str,
    customer_name: str,
    customer_email: str,
    restaurant_name: str,
    restaurant_address: str,
    order_type: str,
    delivery_address: str,
    items: list,
    subtotal: float,
    delivery_fee: float,
    total: float,
    estimated_time: str,
) -> bool:
    """Send HTML order confirmation email. Returns True if sent successfully."""

    api_key  = _get_secret("RESEND_API_KEY")
    from_email = _get_secret("EMAIL_FROM") or "onboarding@resend.dev"

    if not api_key:
        print("RESEND_API_KEY not set — skipping email")
        return False

    # Build items HTML
    items_html = ""
    for item in items:
        items_html += f"""
        <tr>
          <td style="padding:8px 0;border-bottom:1px solid #f0f0f0;">
            {item['name']}
            {'<span style="color:#6b7280;font-size:12px;"> x' + str(item.get('quantity',1)) + '</span>' if item.get('quantity',1) > 1 else ''}
          </td>
          <td style="padding:8px 0;border-bottom:1px solid #f0f0f0;text-align:right;font-weight:600;">
            €{item['price'] * item.get('quantity', 1):.2f}
          </td>
        </tr>"""

    delivery_row = ""
    if order_type == "delivery":
        delivery_row = f"""
        <tr>
          <td style="padding:8px 0;color:#6b7280;">Delivery fee</td>
          <td style="padding:8px 0;text-align:right;color:#6b7280;">€{delivery_fee:.2f}</td>
        </tr>"""

    delivery_info = ""
    if order_type == "delivery":
        delivery_info = f"""
        <div style="background:#f0fdf4;border-radius:8px;padding:16px;margin:16px 0;">
          <p style="margin:0;font-weight:600;color:#15803d;">🚴 Delivery details</p>
          <p style="margin:4px 0 0;color:#374151;">Delivering to: {delivery_address}</p>
          <p style="margin:4px 0 0;color:#374151;">Estimated time: {estimated_time}</p>
        </div>"""
    else:
        delivery_info = f"""
        <div style="background:#eff6ff;border-radius:8px;padding:16px;margin:16px 0;">
          <p style="margin:0;font-weight:600;color:#1d4ed8;">🏃 Pickup details</p>
          <p style="margin:4px 0 0;color:#374151;">Pickup from: {restaurant_address}</p>
          <p style="margin:4px 0 0;color:#374151;">Ready in: {estimated_time}</p>
        </div>"""

    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family:'Helvetica Neue',Arial,sans-serif;background:#f9fafb;margin:0;padding:20px;">
      <div style="max-width:520px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">

        <!-- Header -->
        <div style="background:linear-gradient(135deg,#aa3bff,#6366f1);padding:32px 24px;text-align:center;">
          <p style="margin:0;font-size:32px;">🍛</p>
          <h1 style="margin:8px 0 0;color:#fff;font-size:22px;font-weight:700;">Order Confirmed!</h1>
          <p style="margin:6px 0 0;color:rgba(255,255,255,0.85);font-size:14px;">
            Reference: <strong>{order_ref}</strong>
          </p>
        </div>

        <!-- Body -->
        <div style="padding:24px;">
          <p style="color:#374151;margin:0 0 4px;">Hi {customer_name},</p>
          <p style="color:#6b7280;margin:0 0 20px;font-size:14px;">
            Your order from <strong>{restaurant_name}</strong> has been received!
          </p>

          {delivery_info}

          <!-- Order items -->
          <h3 style="color:#0f0a1e;font-size:15px;margin:0 0 12px;">Your order</h3>
          <table style="width:100%;border-collapse:collapse;">
            {items_html}
            {delivery_row}
            <tr>
              <td style="padding:12px 0 0;font-weight:700;color:#0f0a1e;font-size:16px;">Total</td>
              <td style="padding:12px 0 0;text-align:right;font-weight:700;color:#aa3bff;font-size:16px;">€{total:.2f}</td>
            </tr>
          </table>

          <hr style="border:none;border-top:1px solid #f0f0f0;margin:20px 0;">

          <p style="color:#6b7280;font-size:13px;margin:0;">
            Questions? Reply to this email or contact {restaurant_name} directly.<br>
            Keep your order reference <strong>{order_ref}</strong> handy.
          </p>
        </div>

        <!-- Footer -->
        <div style="background:#f9fafb;padding:16px 24px;text-align:center;">
          <p style="margin:0;color:#9ca3af;font-size:12px;">
            Oulu Restaurant AI · Demo project · {datetime.now().strftime('%d %B %Y')}
          </p>
        </div>

      </div>
    </body>
    </html>
    """

    try:
        import resend
        resend.api_key = api_key
        resend.Emails.send({
            "from":    from_email,
            "to":      [customer_email],
            "subject": f"Order confirmed — {order_ref} | {restaurant_name}",
            "html":    html,
        })
        print(f"Order confirmation sent to {customer_email}")
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False


def send_booking_confirmation(
    booking_ref: str,
    customer_name: str,
    customer_email: str,
    restaurant_name: str,
    restaurant_address: str,
    date: str,
    time: str,
    party_size: int,
    special_requests: str = "",
) -> bool:
    """Send HTML booking confirmation email."""

    api_key    = _get_secret("RESEND_API_KEY")
    from_email = _get_secret("EMAIL_FROM") or "onboarding@resend.dev"

    if not api_key:
        return False

    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family:'Helvetica Neue',Arial,sans-serif;background:#f9fafb;margin:0;padding:20px;">
      <div style="max-width:520px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
        <div style="background:linear-gradient(135deg,#0d9488,#6366f1);padding:32px 24px;text-align:center;">
          <p style="margin:0;font-size:32px;">📅</p>
          <h1 style="margin:8px 0 0;color:#fff;font-size:22px;">Table Booked!</h1>
          <p style="margin:6px 0 0;color:rgba(255,255,255,0.85);font-size:14px;">
            Reference: <strong>{booking_ref}</strong>
          </p>
        </div>
        <div style="padding:24px;">
          <p style="color:#374151;margin:0 0 4px;">Hi {customer_name},</p>
          <p style="color:#6b7280;margin:0 0 20px;font-size:14px;">
            Your table at <strong>{restaurant_name}</strong> is confirmed.
          </p>
          <div style="background:#f0fdf4;border-radius:8px;padding:16px;margin:0 0 20px;">
            <table style="width:100%;">
              <tr><td style="color:#6b7280;font-size:13px;padding:4px 0;">Restaurant</td><td style="font-weight:600;text-align:right;">{restaurant_name}</td></tr>
              <tr><td style="color:#6b7280;font-size:13px;padding:4px 0;">Address</td><td style="text-align:right;font-size:13px;">{restaurant_address}</td></tr>
              <tr><td style="color:#6b7280;font-size:13px;padding:4px 0;">Date</td><td style="font-weight:600;text-align:right;">{date}</td></tr>
              <tr><td style="color:#6b7280;font-size:13px;padding:4px 0;">Time</td><td style="font-weight:600;text-align:right;">{time}</td></tr>
              <tr><td style="color:#6b7280;font-size:13px;padding:4px 0;">Party size</td><td style="font-weight:600;text-align:right;">{party_size} people</td></tr>
              {f'<tr><td style="color:#6b7280;font-size:13px;padding:4px 0;">Special requests</td><td style="text-align:right;font-size:13px;">{special_requests}</td></tr>' if special_requests else ''}
            </table>
          </div>
          <p style="color:#6b7280;font-size:13px;margin:0;">
            To cancel or modify, contact the restaurant directly or reply to this email.<br>
            Reference: <strong>{booking_ref}</strong>
          </p>
        </div>
        <div style="background:#f9fafb;padding:16px 24px;text-align:center;">
          <p style="margin:0;color:#9ca3af;font-size:12px;">
            Oulu Restaurant AI · Demo project · {datetime.now().strftime('%d %B %Y')}
          </p>
        </div>
      </div>
    </body>
    </html>
    """

    try:
        import resend
        resend.api_key = api_key
        resend.Emails.send({
            "from":    from_email,
            "to":      [customer_email],
            "subject": f"Table booked — {booking_ref} | {restaurant_name} {date} {time}",
            "html":    html,
        })
        return True
    except Exception as e:
        print(f"Booking email failed: {e}")
        return False
