"""
test_database.py
─────────────────
Unit tests for database operations.
Uses mocking so tests run without a real Supabase connection.
CircleCI runs these on every push.

Run locally: pytest tests/ -v
"""

import pytest
from unittest.mock import MagicMock, patch
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))


# ── Mock Supabase client ───────────────────────────────────────────────────────
@pytest.fixture
def mock_supabase(monkeypatch):
    """Patch get_supabase to return a mock client."""
    mock = MagicMock()
    monkeypatch.setattr("database.get_supabase", lambda: mock)
    return mock


# ── Restaurant tests ───────────────────────────────────────────────────────────
class TestRestaurantQueries:

    def test_get_all_restaurants_returns_list(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.execute.return_value.data = [
            {"id": 1, "name": "Punjabi Taste", "cuisine": "Pakistani"},
            {"id": 2, "name": "Sauraha",       "cuisine": "Nepali"},
        ]
        import database
        result = database.get_all_restaurants()
        assert len(result) == 2
        assert result[0]["name"] == "Punjabi Taste"

    def test_get_restaurant_by_name_found(self, mock_supabase):
        mock_supabase.table.return_value \
            .select.return_value \
            .ilike.return_value \
            .limit.return_value \
            .execute.return_value.data = [
                {"id": 1, "name": "Punjabi Taste", "capacity": 40}
            ]
        import database
        result = database.get_restaurant_by_name("Punjabi")
        assert result is not None
        assert result["id"] == 1

    def test_get_restaurant_by_name_not_found(self, mock_supabase):
        mock_supabase.table.return_value \
            .select.return_value \
            .ilike.return_value \
            .limit.return_value \
            .execute.return_value.data = []
        import database
        result = database.get_restaurant_by_name("NonExistent")
        assert result is None

    def test_get_restaurants_by_feature(self, mock_supabase):
        mock_supabase.table.return_value \
            .select.return_value \
            .contains.return_value \
            .execute.return_value.data = [
                {"id": 1, "name": "Punjabi Taste", "features": ["halal", "vegan"]},
                {"id": 5, "name": "Spice Garden",  "features": ["vegan"]},
            ]
        import database
        result = database.get_restaurants_by_feature("vegan")
        assert len(result) == 2


# ── Availability tests ─────────────────────────────────────────────────────────
class TestAvailability:

    def test_get_available_slots_returns_open_slots(self, mock_supabase):
        mock_supabase.table.return_value \
            .select.return_value \
            .eq.return_value \
            .eq.return_value \
            .execute.return_value.data = [
                {"id": 1, "time": "18:00", "capacity": 10, "booked_seats": 4},
                {"id": 2, "time": "19:00", "capacity": 10, "booked_seats": 10},  # full
                {"id": 3, "time": "20:00", "capacity": 10, "booked_seats": 0},
            ]
        import database
        slots = database.get_available_slots(1, "2026-06-15", party_size=4)
        # 19:00 slot is full (10-10=0 < 4), should be excluded
        assert len(slots) == 2
        times = [s["time"] for s in slots]
        assert "18:00" in times
        assert "20:00" in times
        assert "19:00" not in times

    def test_no_slots_when_fully_booked(self, mock_supabase):
        mock_supabase.table.return_value \
            .select.return_value \
            .eq.return_value \
            .eq.return_value \
            .execute.return_value.data = [
                {"id": 1, "time": "18:00", "capacity": 4, "booked_seats": 4},
            ]
        import database
        slots = database.get_available_slots(1, "2026-06-15", party_size=2)
        assert len(slots) == 0

    def test_is_restaurant_open_on_open_day(self, mock_supabase):
        mock_supabase.table.return_value \
            .select.return_value \
            .eq.return_value \
            .single.return_value \
            .execute.return_value.data = {
                "id": 1,
                "opening_hours": {
                    "monday": "11:00–21:00",
                    "tuesday": "closed",
                }
            }
        import database
        # Monday 2026-06-15 is a Monday
        is_open, hours = database.is_restaurant_open(1, "2026-06-15")
        assert is_open is True
        assert hours == "11:00–21:00"

    def test_is_restaurant_closed_on_closed_day(self, mock_supabase):
        mock_supabase.table.return_value \
            .select.return_value \
            .eq.return_value \
            .single.return_value \
            .execute.return_value.data = {
                "id": 1,
                "opening_hours": {"tuesday": "closed"}
            }
        import database
        # 2026-06-16 is a Tuesday
        is_open, hours = database.is_restaurant_open(1, "2026-06-16")
        assert is_open is False
        assert hours == "closed"


# ── Booking tests ──────────────────────────────────────────────────────────────
class TestBookings:

    def test_create_booking_success(self, mock_supabase):
        mock_supabase.table.return_value \
            .insert.return_value \
            .execute.return_value.data = [{
                "id": 1,
                "booking_ref": "OUL-TEST1",
                "status": "confirmed",
            }]
        mock_supabase.rpc.return_value.execute.return_value = MagicMock()

        import database
        booking = database.create_booking(
            restaurant_id=1,
            slot_id=1,
            date_str="2026-06-20",
            time_str="19:00",
            party_size=2,
            customer_name="Test User",
            customer_email="test@example.com",
        )
        assert booking["booking_ref"] == "OUL-TEST1"
        assert booking["status"] == "confirmed"

    def test_cancel_booking_success(self, mock_supabase):
        # get_booking_by_ref returns a booking
        mock_supabase.table.return_value \
            .select.return_value \
            .eq.return_value \
            .single.return_value \
            .execute.return_value.data = {
                "booking_ref": "OUL-TEST1",
                "status": "confirmed",
                "slot_id": 1,
                "party_size": 2,
            }
        mock_supabase.table.return_value \
            .update.return_value \
            .eq.return_value \
            .execute.return_value = MagicMock()
        mock_supabase.rpc.return_value.execute.return_value = MagicMock()

        import database
        result = database.cancel_booking("OUL-TEST1")
        assert result is True

    def test_cancel_already_cancelled_booking(self, mock_supabase):
        mock_supabase.table.return_value \
            .select.return_value \
            .eq.return_value \
            .single.return_value \
            .execute.return_value.data = {
                "booking_ref": "OUL-TEST1",
                "status": "cancelled",  # already cancelled
                "slot_id": 1,
                "party_size": 2,
            }
        import database
        result = database.cancel_booking("OUL-TEST1")
        assert result is False

    def test_booking_ref_format(self):
        import database
        ref = database._generate_booking_ref()
        assert ref.startswith("OUL-")
        assert len(ref) == 9   # OUL- (4) + 5 chars


# ── Menu tests ─────────────────────────────────────────────────────────────────
class TestMenu:

    def test_get_menu_returns_items(self, mock_supabase):
        mock_supabase.table.return_value \
            .select.return_value \
            .eq.return_value \
            .order.return_value \
            .execute.return_value.data = [
                {"id": 1, "name": "Butter Chicken", "price": 15.90,
                 "category": "Main", "vegetarian": False},
                {"id": 2, "name": "Palak Paneer",   "price": 14.90,
                 "category": "Main", "vegetarian": True},
            ]
        import database
        menu = database.get_menu(1)
        assert len(menu) == 2
        veg_items = [i for i in menu if i["vegetarian"]]
        assert len(veg_items) == 1
        assert veg_items[0]["name"] == "Palak Paneer"

    def test_search_menu_vegan_filter(self, mock_supabase):
        q = (mock_supabase.table.return_value
             .select.return_value
             .ilike.return_value
             .lte.return_value
             .eq.return_value   # vegetarian=True
             .eq.return_value)  # vegan=True
        q.execute.return_value.data = [
            {"id": 3, "name": "Dal Makhani", "vegan": True, "vegetarian": True},
        ]
        import database
        results = database.search_menu_items("dal", vegan=True)
        assert len(results) == 1


# ── Date parsing tests ─────────────────────────────────────────────────────────
class TestDateParsing:

    def test_parse_tomorrow(self):
        from agent import _parse_date
        from datetime import datetime, timedelta
        result = _parse_date("tomorrow")
        expected = (datetime.now().date() + timedelta(days=1)).strftime("%Y-%m-%d")
        assert result == expected

    def test_parse_today(self):
        from agent import _parse_date
        from datetime import datetime
        result = _parse_date("today")
        expected = datetime.now().date().strftime("%Y-%m-%d")
        assert result == expected

    def test_parse_iso_date(self):
        from agent import _parse_date
        result = _parse_date("2026-07-15")
        assert result == "2026-07-15"

    def test_parse_dot_format(self):
        from agent import _parse_date
        result = _parse_date("15.07.2026")
        assert result == "2026-07-15"

    def test_parse_empty_returns_none(self):
        from agent import _parse_date
        result = _parse_date("")
        assert result is None

    def test_parse_invalid_returns_none(self):
        from agent import _parse_date
        result = _parse_date("not a date")
        assert result is None
