"""
test_agent_tools.py
────────────────────
Tests for agent tool logic — mocks LLM and DB calls.
"""

import pytest
import json
from unittest.mock import MagicMock, patch
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))


class TestCheckAvailabilityTool:

    def test_valid_input_with_slots(self):
        with patch("database.get_restaurant_by_name") as mock_rest, \
             patch("database.is_restaurant_open") as mock_open, \
             patch("database.get_available_slots") as mock_slots:

            mock_rest.return_value = {
                "id": 1, "name": "Punjabi Taste", "capacity": 40
            }
            mock_open.return_value  = (True, "11:00–21:00")
            mock_slots.return_value = [
                {"slot_id": 1, "time": "18:00", "remaining": 6},
                {"slot_id": 2, "time": "19:00", "remaining": 4},
            ]

            from agent import check_availability
            result = check_availability.invoke(json.dumps({
                "restaurant_name": "Punjabi Taste",
                "date": "2026-07-10",
                "party_size": 2,
            }))
            assert "18:00" in result
            assert "19:00" in result
            assert "Punjabi Taste" in result

    def test_restaurant_closed(self):
        with patch("database.get_restaurant_by_name") as mock_rest, \
             patch("database.is_restaurant_open") as mock_open:

            mock_rest.return_value = {"id": 4, "name": "Garam Masala"}
            mock_open.return_value = (False, "closed")

            from agent import check_availability
            result = check_availability.invoke(json.dumps({
                "restaurant_name": "Garam Masala",
                "date": "2026-06-15",
                "party_size": 2,
            }))
            assert "closed" in result.lower()

    def test_missing_restaurant(self):
        with patch("database.get_restaurant_by_name") as mock_rest:
            mock_rest.return_value = None

            from agent import check_availability
            result = check_availability.invoke(json.dumps({
                "restaurant_name": "NonExistent",
                "date": "2026-07-10",
                "party_size": 2,
            }))
            assert "not found" in result.lower()

    def test_invalid_json(self):
        from agent import check_availability
        result = check_availability.invoke("not json at all")
        assert "invalid" in result.lower()


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
            result = make_booking.invoke(json.dumps({
                "restaurant_name": "Punjabi Taste",
                "date": "2026-07-10",
                "time": "19:00",
                "party_size": 2,
                "customer_name": "Anna Test",
                "customer_email": "anna@test.fi",
            }))
            assert "OUL-ABC12" in result
            assert "confirmed" in result.lower()

    def test_missing_required_fields(self):
        from agent import make_booking
        result = make_booking.invoke(json.dumps({
            "restaurant_name": "Punjabi Taste",
            # missing date, time, party_size, name, email
        }))
        assert "missing" in result.lower()

    def test_time_slot_unavailable(self):
        with patch("database.get_restaurant_by_name") as mock_rest, \
             patch("database.get_available_slots") as mock_slots:

            mock_rest.return_value = {"id": 1, "name": "Punjabi Taste"}
            mock_slots.return_value = [
                {"slot_id": 5, "time": "18:00", "remaining": 4}  # 19:00 not available
            ]

            from agent import make_booking
            result = make_booking.invoke(json.dumps({
                "restaurant_name": "Punjabi Taste",
                "date": "2026-07-10",
                "time": "19:00",
                "party_size": 2,
                "customer_name": "Test",
                "customer_email": "test@test.fi",
            }))
            assert "not available" in result.lower()
            assert "18:00" in result  # suggests alternative


class TestSearchRestaurantsTool:

    def test_search_by_feature(self):
        with patch("database.get_all_restaurants") as mock_all:
            mock_all.return_value = [
                {"id": 1, "name": "Punjabi Taste", "cuisine": "Pakistani",
                 "features": ["halal", "vegan"], "price_range": "€10–25",
                 "rating": 4.9, "address": "Addr 1", "description": "Great food"},
                {"id": 2, "name": "Sauraha", "cuisine": "Nepali",
                 "features": ["vegetarian"], "price_range": "€12–28",
                 "rating": 4.5, "address": "Addr 2", "description": "Nepali food"},
            ]
            from agent import search_restaurants
            result = search_restaurants.invoke("vegan")
            assert "Punjabi Taste" in result

    def test_search_returns_all_when_no_match(self):
        with patch("database.get_all_restaurants") as mock_all:
            mock_all.return_value = [
                {"id": 1, "name": "Punjabi Taste", "cuisine": "Pakistani",
                 "features": [], "price_range": "€10–25", "rating": 4.9,
                 "address": "Addr 1", "description": "Food"},
            ]
            from agent import search_restaurants
            result = search_restaurants.invoke("xyz_not_found")
            # Should return all restaurants when nothing matches
            assert "Punjabi Taste" in result


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
            result = manage_booking.invoke(json.dumps({
                "action": "lookup",
                "booking_ref": "OUL-TEST1",
            }))
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
            result = manage_booking.invoke(json.dumps({
                "action": "cancel",
                "booking_ref": "OUL-TEST1",
            }))
            assert "cancelled" in result.lower()

    def test_booking_not_found(self):
        with patch("database.get_booking_by_ref") as mock_get:
            mock_get.return_value = None

            from agent import manage_booking
            result = manage_booking.invoke(json.dumps({
                "action": "lookup",
                "booking_ref": "OUL-XXXXX",
            }))
            assert "no booking found" in result.lower()
