"""
test_agent_tools.py — calls tool.func() directly to bypass LangChain's
Pydantic wrapper; tests logic, not serialisation.
"""

import pytest
from unittest.mock import MagicMock, patch
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))


class TestCheckAvailabilityTool:

    def test_valid_input_with_slots(self):
        with patch("database.get_restaurant_by_name") as mock_rest, \
             patch("database.is_restaurant_open") as mock_open, \
             patch("database.get_available_slots") as mock_slots:

            mock_rest.return_value = {"id": 1, "name": "Punjabi Taste", "capacity": 40}
            mock_open.return_value  = (True, "11:00-21:00")
            mock_slots.return_value = [
                {"slot_id": 1, "time": "18:00", "remaining": 6},
                {"slot_id": 2, "time": "19:00", "remaining": 4},
            ]

            from agent import check_availability
            result = check_availability.func(
                restaurant_name="Punjabi Taste",
                date="2026-07-10",
                party_size=2,
            )
            assert "18:00" in result
            assert "Punjabi Taste" in result

    def test_restaurant_closed(self):
        with patch("database.get_restaurant_by_name") as mock_rest, \
             patch("database.is_restaurant_open") as mock_open:

            mock_rest.return_value = {"id": 4, "name": "Garam Masala"}
            mock_open.return_value = (False, "closed")

            from agent import check_availability
            result = check_availability.func(
                restaurant_name="Garam Masala",
                date="2026-06-15",
                party_size=2,
            )
            assert "closed" in result.lower()

    def test_missing_restaurant(self):
        with patch("database.get_restaurant_by_name") as mock_rest:
            mock_rest.return_value = None

            from agent import check_availability
            result = check_availability.func(
                restaurant_name="NonExistent",
                date="2026-07-10",
                party_size=2,
            )
            assert "not found" in result.lower()

    def test_invalid_json(self):
        """Passing garbage string should return not-found, not crash."""
        with patch("database.get_restaurant_by_name") as mock_rest:
            mock_rest.return_value = None

            from agent import check_availability
            result = check_availability.func(
                restaurant_name="not json at all",
                date="2026-07-10",
                party_size=2,
            )
            assert "not found" in result.lower()


class TestMakeBookingTool:

    def test_successful_booking(self):
        with patch("database.get_restaurant_by_name") as mock_rest, \
             patch("database.get_available_slots") as mock_slots, \
             patch("database.create_booking") as mock_create:

            mock_rest.return_value = {
                "id": 1, "name": "Punjabi Taste",
                "address": "Harjapäänkatu 33"
            }
            mock_slots.return_value = [
                {"slot_id": 5, "time": "19:00", "remaining": 4}
            ]
            mock_create.return_value = {
                "booking_ref": "OUL-ABC12",
                "status": "confirmed",
            }

            from agent import make_booking
            result = make_booking.func(
                restaurant_name="Punjabi Taste",
                date="2026-07-10",
                time="19:00",
                party_size=2,
                customer_name="Anna Test",
                customer_email="anna@test.fi",
            )
            assert "OUL-ABC12" in result
            assert "confirmed" in result.lower()

    def test_missing_required_fields(self):
        """Missing date/time/email — restaurant lookup still works, slots empty."""
        with patch("database.get_restaurant_by_name") as mock_rest, \
             patch("database.get_available_slots") as mock_slots:

            mock_rest.return_value = {"id": 1, "name": "Punjabi Taste"}
            mock_slots.return_value = []

            from agent import make_booking
            result = make_booking.func(
                restaurant_name="Punjabi Taste",
                date="2026-07-10",
                time="19:00",
                party_size=2,
                customer_name="",
                customer_email="",
            )
            # No slots available for empty time
            assert "not available" in result.lower() or "none" in result.lower()

    def test_time_slot_unavailable(self):
        with patch("database.get_restaurant_by_name") as mock_rest, \
             patch("database.get_available_slots") as mock_slots:

            mock_rest.return_value = {"id": 1, "name": "Punjabi Taste"}
            mock_slots.return_value = [
                {"slot_id": 5, "time": "18:00", "remaining": 4}
            ]

            from agent import make_booking
            result = make_booking.func(
                restaurant_name="Punjabi Taste",
                date="2026-07-10",
                time="19:00",
                party_size=2,
                customer_name="Test",
                customer_email="test@test.fi",
            )
            assert "not available" in result.lower() or "18:00" in result


class TestSearchRestaurantsTool:

    # Shared mock data including Aura Himalaya (Indo-Chinese, Saaristonkatu 5)
    MOCK_RESTAURANTS = [
        {"id": 1, "name": "Punjabi Taste", "cuisine": "Pakistani",
         "features": ["halal", "vegan"], "price_range": "€10-25",
         "rating": 4.9, "address": "Harjapäänkatu 33", "description": "Authentic Pakistani cuisine"},
        {"id": 2, "name": "Sauraha", "cuisine": "Nepali",
         "features": ["vegetarian"], "price_range": "€12-28",
         "rating": 4.5, "address": "Addr 2", "description": "Nepali food"},
        {"id": 6, "name": "Aura Himalaya", "cuisine": "Indo-Chinese / Nepali",
         "features": ["lunch buffet", "halal", "vegetarian", "sizzler"],
         "price_range": "€9-26", "rating": 4.6,
         "address": "Saaristonkatu 5, 90100 Oulu",
         "description": "Indo-Chinese restaurant blending Himalayan spices with Chinese wok cooking. "
                        "Famous for the flaming Nepal Top Sizzler and daily lunch buffet."},
    ]

    def test_search_by_feature(self):
        with patch("database.get_all_restaurants") as mock_all:
            mock_all.return_value = self.MOCK_RESTAURANTS
            from agent import search_restaurants
            result = search_restaurants.func("vegan")
            assert "Punjabi Taste" in result

    def test_search_aura_himalaya_by_cuisine(self):
        """Aura Himalaya should appear when searching for Indo-Chinese or Himalayan."""
        with patch("database.get_all_restaurants") as mock_all:
            mock_all.return_value = self.MOCK_RESTAURANTS
            from agent import search_restaurants
            result = search_restaurants.func("Indo-Chinese")
            assert "Aura Himalaya" in result

    def test_search_aura_himalaya_lunch_buffet(self):
        """Searching 'lunch buffet' should surface Aura Himalaya."""
        with patch("database.get_all_restaurants") as mock_all:
            mock_all.return_value = self.MOCK_RESTAURANTS
            from agent import search_restaurants
            result = search_restaurants.func("lunch buffet")
            assert "Aura Himalaya" in result

    def test_search_returns_all_when_no_match(self):
        with patch("database.get_all_restaurants") as mock_all:
            mock_all.return_value = self.MOCK_RESTAURANTS
            from agent import search_restaurants
            result = search_restaurants.func("xyz_not_found")
            # Falls back to showing all restaurants
            assert "Punjabi Taste" in result

    def test_all_restaurants_returned_on_empty_query(self):
        """Empty/generic query should return the full list including new restaurants."""
        with patch("database.get_all_restaurants") as mock_all:
            mock_all.return_value = self.MOCK_RESTAURANTS
            from agent import search_restaurants
            result = search_restaurants.func("restaurant")
            assert "Aura Himalaya" in result or "Punjabi Taste" in result


class TestManageBookingTool:

    def test_lookup_by_ref(self):
        with patch("database.get_booking_by_ref") as mock_get:
            mock_get.return_value = {
                "booking_ref": "OUL-TEST1",
                "date": "2026-07-10",
                "time": "19:00",
                "party_size": 2,
                "customer_name": "Test User",
                "customer_email": "test@test.fi",
                "status": "confirmed",
                "special_requests": "",
                "restaurants": {"name": "Punjabi Taste"},
            }
            from agent import manage_booking
            result = manage_booking.func(
                action="lookup",
                booking_ref="OUL-TEST1",
            )
            assert "OUL-TEST1" in result
            assert "Punjabi Taste" in result

    def test_cancel_booking(self):
        with patch("database.get_booking_by_ref") as mock_get, \
             patch("database.cancel_booking") as mock_cancel:

            mock_get.return_value = {
                "booking_ref": "OUL-TEST1",
                "date": "2026-07-10",
                "time": "19:00",
                "party_size": 2,
                "status": "confirmed",
                "restaurants": {"name": "Punjabi Taste"},
            }
            mock_cancel.return_value = True

            from agent import manage_booking
            result = manage_booking.func(
                action="cancel",
                booking_ref="OUL-TEST1",
            )
            assert "cancel" in result.lower()

    def test_booking_not_found(self):
        with patch("database.get_booking_by_ref") as mock_get:
            mock_get.return_value = None

            from agent import manage_booking
            result = manage_booking.func(
                action="lookup",
                booking_ref="OUL-XXXXX",
            )
            assert "no booking found" in result.lower() or "OUL-XXXXX" in result


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

    def test_parse_empty_returns_none(self):
        from agent import _parse_date
        result = _parse_date("")
        assert result is None
