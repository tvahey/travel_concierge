"""State management for Travel Concierge Agent."""

from dataclasses import dataclass, field
from typing import Any, Dict, List
from datetime import datetime, timezone


@dataclass
class MemoryNote:
    """A single memory note with metadata."""
    text: str
    last_update_date: str
    keywords: List[str]

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "last_update_date": self.last_update_date,
            "keywords": self.keywords,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryNote":
        return cls(
            text=data.get("text", ""),
            last_update_date=data.get("last_update_date", ""),
            keywords=data.get("keywords", []),
        )


@dataclass
class TravelState:
    """State object for the Travel Concierge Agent."""

    profile: Dict[str, Any] = field(default_factory=dict)

    # Long-term memory
    global_memory: Dict[str, Any] = field(default_factory=lambda: {"notes": []})

    # Short-term memory (staging for consolidation)
    session_memory: Dict[str, Any] = field(default_factory=lambda: {"notes": []})

    # Trip history (recent trips)
    trip_history: Dict[str, Any] = field(default_factory=lambda: {"trips": []})

    # Rendered injection strings (computed per run)
    system_frontmatter: str = ""
    global_memories_md: str = ""
    session_memories_md: str = ""

    # Flag for triggering session injection after context trimming
    inject_session_memories_next_turn: bool = False

    def to_dict(self) -> dict:
        """Convert state to dictionary for JSON serialization."""
        return {
            "profile": self.profile,
            "global_memory": self.global_memory,
            "session_memory": self.session_memory,
            "trip_history": self.trip_history,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TravelState":
        """Create state from dictionary."""
        return cls(
            profile=data.get("profile", {}),
            global_memory=data.get("global_memory", {"notes": []}),
            session_memory=data.get("session_memory", {"notes": []}),
            trip_history=data.get("trip_history", {"trips": []}),
        )


def get_default_user_state() -> TravelState:
    """Create a default user state with sample data."""
    return TravelState(
        profile={
            "global_customer_id": "crm_12345",
            "name": "John Doe",
            "age": "31",
            "home_city": "San Francisco",
            "currency": "USD",
            "passport_expiry_date": "2029-06-12",
            "frequent_flyer_programs": [
                {"program": "United MileagePlus", "member_id": "AB123456", "status": "Gold", "active": True},
                {"program": "Delta SkyMiles", "member_id": "CD789012", "status": "Silver", "active": False},
                {"program": "American AAdvantage", "member_id": "EF345678", "status": "Platinum", "active": False},
            ],
            "hotel_loyalty_programs": [
                {"program": "Marriott Bonvoy", "member_id": "MR998877", "status": "Titanium", "active": True},
                {"program": "Hilton Honors", "member_id": "HH445566", "status": "Gold", "active": False},
                {"program": "Hyatt", "member_id": "HY112233", "status": "Explorist", "active": False},
            ],
            # Flight Preferences
            "flight_preferences": {
                "home_airport": "SFO",
                "seat_preference": "aisle",
                "departure_time": "morning",  # morning, afternoon, evening
                "cabin_class": "economy",  # economy, premium_economy, business, first
                "max_layovers": 1,
                "avoid_red_eye": True,
            },
            # Hotel Preferences
            "hotel_preferences": {
                "preferred_brands": ["Marriott", "Hilton"],
                "min_stars": 4,
                "on_airport": False,
                "prefer_high_floor": True,
                "bed_type": "king",
                "smoking": False,
            },
            # Car Rental Preferences
            "car_preferences": {
                "preferred_size": "midsize",  # compact, midsize, full-size, suv, luxury
                "on_airport": True,
                "preferred_companies": [],
            },
            "tone": "concise and friendly",
            "active_visas": ["Schengen", "US"],
            "insurance_coverage_profile": {
                "car_rental": "primary_cdw_included",
                "travel_medical": "covered",
            },
        },
        global_memory={
            "notes": [
                {
                    "text": "For trips shorter than a week, user generally prefers not to check bags.",
                    "last_update_date": "2025-04-05",
                    "keywords": ["baggage", "short_trip"],
                },
                {
                    "text": "User usually prefers aisle seats.",
                    "last_update_date": "2024-06-25",
                    "keywords": ["seat_preference"],
                },
                {
                    "text": "User generally likes central, walkable city-center neighborhoods.",
                    "last_update_date": "2024-02-11",
                    "keywords": ["neighborhood"],
                },
                {
                    "text": "User generally likes to compare options side-by-side",
                    "last_update_date": "2023-02-17",
                    "keywords": ["pricing"],
                },
                {
                    "text": "User prefers high floors",
                    "last_update_date": "2023-02-11",
                    "keywords": ["room"],
                },
            ]
        },
        trip_history={
            "trips": [
                {
                    "from_city": "Istanbul",
                    "from_country": "Turkey",
                    "to_city": "Paris",
                    "to_country": "France",
                    "check_in_date": "2025-05-01",
                    "check_out_date": "2025-05-03",
                    "trip_purpose": "leisure",
                    "party_size": 1,
                    "flight": {
                        "airline": "United",
                        "airline_status_at_booking": "United Gold",
                        "cabin_class": "economy_plus",
                        "seat_selected": "aisle",
                        "seat_location": "front",
                        "layovers": 1,
                        "baggage": {"checked_bags": 0, "carry_ons": 1},
                        "special_requests": ["vegetarian_meal"],
                    },
                    "hotel": {
                        "brand": "Hilton",
                        "property_name": "Hilton Paris Opera",
                        "neighborhood": "city_center",
                        "bed_type": "king",
                        "smoking": "non_smoking",
                        "high_floor": True,
                        "early_check_in": False,
                        "late_check_out": True,
                    },
                }
            ]
        },
    )


def today_iso_utc() -> str:
    """Get today's date in ISO format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT")
