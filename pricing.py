"""Amadeus API integration for real-time flight and hotel pricing."""

import os
from datetime import datetime
from typing import Optional
from urllib.parse import quote, urlencode

try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

from amadeus import Client, ResponseError

from logger import get_logger


def get_secret(key: str, default: str = None) -> str:
    """Get secret from Streamlit secrets (cloud) or environment variables (local)."""
    # Try Streamlit secrets first (for Streamlit Cloud deployment)
    if HAS_STREAMLIT:
        try:
            if hasattr(st, 'secrets') and key in st.secrets:
                return st.secrets[key]
        except Exception:
            pass
    # Fall back to environment variables (for local development)
    return os.getenv(key, default)

logger = get_logger(__name__)


# Airline codes to names and booking URLs
AIRLINE_INFO = {
    "UA": {"name": "United Airlines", "url": "https://www.united.com"},
    "AA": {"name": "American Airlines", "url": "https://www.aa.com"},
    "DL": {"name": "Delta Air Lines", "url": "https://www.delta.com"},
    "WN": {"name": "Southwest Airlines", "url": "https://www.southwest.com"},
    "B6": {"name": "JetBlue", "url": "https://www.jetblue.com"},
    "AS": {"name": "Alaska Airlines", "url": "https://www.alaskaair.com"},
    "NK": {"name": "Spirit Airlines", "url": "https://www.spirit.com"},
    "F9": {"name": "Frontier Airlines", "url": "https://www.flyfrontier.com"},
    "BA": {"name": "British Airways", "url": "https://www.britishairways.com"},
    "LH": {"name": "Lufthansa", "url": "https://www.lufthansa.com"},
    "AF": {"name": "Air France", "url": "https://www.airfrance.com"},
    "KL": {"name": "KLM", "url": "https://www.klm.com"},
    "EK": {"name": "Emirates", "url": "https://www.emirates.com"},
    "QR": {"name": "Qatar Airways", "url": "https://www.qatarairways.com"},
    "SQ": {"name": "Singapore Airlines", "url": "https://www.singaporeair.com"},
    "CX": {"name": "Cathay Pacific", "url": "https://www.cathaypacific.com"},
    "NH": {"name": "ANA", "url": "https://www.ana.co.jp"},
    "JL": {"name": "Japan Airlines", "url": "https://www.jal.co.jp"},
    "AC": {"name": "Air Canada", "url": "https://www.aircanada.com"},
    "QF": {"name": "Qantas", "url": "https://www.qantas.com"},
}

# Hotel brand URLs
HOTEL_BRAND_URLS = {
    "marriott": "https://www.marriott.com",
    "hilton": "https://www.hilton.com",
    "hyatt": "https://www.hyatt.com",
    "ihg": "https://www.ihg.com",
    "wyndham": "https://www.wyndham.com",
    "bestwestern": "https://www.bestwestern.com",
    "accor": "https://www.accor.com",
    "radisson": "https://www.radissonhotels.com",
    "choice": "https://www.choicehotels.com",
}


def _get_google_flights_url(origin: str, destination: str, departure_date: str, return_date: Optional[str] = None) -> str:
    """Generate Google Flights search URL."""
    # Google Flights URL format
    base_url = "https://www.google.com/travel/flights"
    params = {
        "q": f"flights from {origin} to {destination}",
        "curr": "USD",
    }
    # Add dates to query
    date_str = f" on {departure_date}"
    if return_date:
        date_str += f" returning {return_date}"
    params["q"] += date_str

    return f"{base_url}?{urlencode(params)}"


def _get_kayak_flights_url(origin: str, destination: str, departure_date: str, return_date: Optional[str] = None) -> str:
    """Generate Kayak flight search URL."""
    if return_date:
        return f"https://www.kayak.com/flights/{origin}-{destination}/{departure_date}/{return_date}"
    return f"https://www.kayak.com/flights/{origin}-{destination}/{departure_date}"


def _get_skyscanner_flights_url(origin: str, destination: str, departure_date: str, return_date: Optional[str] = None) -> str:
    """Generate Skyscanner flight search URL."""
    dep_date = departure_date.replace("-", "")[:6]  # YYYYMM format
    if return_date:
        ret_date = return_date.replace("-", "")[:6]
        return f"https://www.skyscanner.com/transport/flights/{origin.lower()}/{destination.lower()}/{dep_date}/{ret_date}/"
    return f"https://www.skyscanner.com/transport/flights/{origin.lower()}/{destination.lower()}/{dep_date}/"


def _get_airline_info(carrier_code: str) -> dict:
    """Get airline name and URL from carrier code."""
    info = AIRLINE_INFO.get(carrier_code.upper(), {})
    return {
        "name": info.get("name", carrier_code),
        "url": info.get("url", f"https://www.google.com/search?q={carrier_code}+airline+booking"),
    }


def _get_google_hotels_url(city: str, check_in: str, check_out: str) -> str:
    """Generate Google Hotels search URL."""
    params = {
        "q": f"hotels in {city}",
        "dates": f"{check_in}_{check_out}",
    }
    return f"https://www.google.com/travel/hotels?{urlencode(params)}"


def _get_booking_com_url(city: str, check_in: str, check_out: str, adults: int = 1) -> str:
    """Generate Booking.com search URL."""
    params = {
        "ss": city,
        "checkin": check_in,
        "checkout": check_out,
        "group_adults": adults,
    }
    return f"https://www.booking.com/searchresults.html?{urlencode(params)}"


def _get_hotels_com_url(city: str, check_in: str, check_out: str) -> str:
    """Generate Hotels.com search URL."""
    params = {
        "q-destination": city,
        "q-check-in": check_in,
        "q-check-out": check_out,
    }
    return f"https://www.hotels.com/search.do?{urlencode(params)}"


def get_amadeus_client() -> Optional[Client]:
    """Get Amadeus API client."""
    api_key = get_secret("AMADEUS_API_KEY")
    api_secret = get_secret("AMADEUS_API_SECRET")

    if not api_key or not api_secret:
        return None

    return Client(
        client_id=api_key,
        client_secret=api_secret,
        hostname="test"  # Use "production" for live data
    )


def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str] = None,
    adults: int = 1,
    cabin_class: str = "ECONOMY",
    max_results: int = 5,
) -> dict:
    """
    Search for flight offers.

    Args:
        origin: Origin airport IATA code (e.g., "SFO")
        destination: Destination airport IATA code (e.g., "JFK")
        departure_date: Departure date in YYYY-MM-DD format
        return_date: Optional return date for round-trip
        adults: Number of adult passengers
        cabin_class: ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST
        max_results: Maximum number of results to return

    Returns:
        Dictionary with flight offers or error message
    """
    client = get_amadeus_client()

    if not client:
        return {
            "error": "Amadeus API not configured. Please add AMADEUS_API_KEY and AMADEUS_API_SECRET to your .env file.",
            "setup_url": "https://developers.amadeus.com"
        }

    try:
        search_params = {
            "originLocationCode": origin.upper(),
            "destinationLocationCode": destination.upper(),
            "departureDate": departure_date,
            "adults": adults,
            "travelClass": cabin_class,
            "max": max_results,
            "currencyCode": "USD",
        }

        if return_date:
            search_params["returnDate"] = return_date

        response = client.shopping.flight_offers_search.get(**search_params)

        flights = []
        for offer in response.data:
            # Parse itineraries
            itineraries = []
            carriers_in_offer = set()
            for itinerary in offer.get("itineraries", []):
                segments = []
                for segment in itinerary.get("segments", []):
                    carrier_code = segment["carrierCode"]
                    carriers_in_offer.add(carrier_code)
                    airline_info = _get_airline_info(carrier_code)
                    segments.append({
                        "departure": {
                            "airport": segment["departure"]["iataCode"],
                            "time": segment["departure"]["at"],
                        },
                        "arrival": {
                            "airport": segment["arrival"]["iataCode"],
                            "time": segment["arrival"]["at"],
                        },
                        "carrier": carrier_code,
                        "carrier_name": airline_info["name"],
                        "carrier_url": airline_info["url"],
                        "flight_number": segment["number"],
                        "duration": segment.get("duration", ""),
                    })
                itineraries.append({
                    "duration": itinerary.get("duration", ""),
                    "segments": segments,
                })

            # Get booking links for all carriers in this offer
            airline_booking_links = []
            for carrier in carriers_in_offer:
                info = _get_airline_info(carrier)
                airline_booking_links.append({
                    "name": info["name"],
                    "url": info["url"],
                })

            flights.append({
                "id": offer["id"],
                "price": {
                    "total": offer["price"]["total"],
                    "currency": offer["price"]["currency"],
                },
                "itineraries": itineraries,
                "seats_available": offer.get("numberOfBookableSeats", "N/A"),
                "booking_links": {
                    "airlines": airline_booking_links,
                },
            })

        # Generate search links for the overall search
        search_links = {
            "google_flights": _get_google_flights_url(origin, destination, departure_date, return_date),
            "kayak": _get_kayak_flights_url(origin, destination, departure_date, return_date),
            "skyscanner": _get_skyscanner_flights_url(origin, destination, departure_date, return_date),
        }

        return {
            "success": True,
            "count": len(flights),
            "flights": flights,
            "search_links": search_links,
            "citation": "⚠️ Prices and times are ESTIMATES from Amadeus test data - verify on booking sites for actual rates.",
        }

    except ResponseError as e:
        logger.error(f"Amadeus flight search error: {e.response.body}")
        return {
            "error": f"Amadeus API error: {e.response.body}",
            "success": False,
        }
    except Exception as e:
        logger.error(f"Flight search error: {str(e)}")
        return {
            "error": f"Error searching flights: {str(e)}",
            "success": False,
        }


def search_hotels(
    city_code: str,
    check_in_date: str,
    check_out_date: str,
    adults: int = 1,
    rooms: int = 1,
    max_results: int = 5,
) -> dict:
    """
    Search for hotel offers in a city.

    Args:
        city_code: City IATA code (e.g., "NYC", "PAR", "LON")
        check_in_date: Check-in date in YYYY-MM-DD format
        check_out_date: Check-out date in YYYY-MM-DD format
        adults: Number of adult guests
        rooms: Number of rooms
        max_results: Maximum number of results to return

    Returns:
        Dictionary with hotel offers or error message
    """
    client = get_amadeus_client()

    if not client:
        return {
            "error": "Amadeus API not configured. Please add AMADEUS_API_KEY and AMADEUS_API_SECRET to your .env file.",
            "setup_url": "https://developers.amadeus.com"
        }

    try:
        # First, get hotels in the city
        hotels_response = client.reference_data.locations.hotels.by_city.get(
            cityCode=city_code.upper(),
        )

        if not hotels_response.data:
            return {
                "success": True,
                "count": 0,
                "hotels": [],
                "message": f"No hotels found in {city_code}",
            }

        # Get hotel IDs (limit to avoid too many API calls)
        hotel_ids = [h["hotelId"] for h in hotels_response.data[:20]]

        # Search for offers at these hotels
        offers_response = client.shopping.hotel_offers_search.get(
            hotelIds=hotel_ids,
            checkInDate=check_in_date,
            checkOutDate=check_out_date,
            adults=adults,
            roomQuantity=rooms,
        )

        hotels = []
        for hotel_offer in offers_response.data[:max_results]:
            hotel = hotel_offer.get("hotel", {})
            offers = hotel_offer.get("offers", [])

            if offers:
                best_offer = offers[0]
                hotel_name = hotel.get("name", "Unknown")

                # Try to find hotel brand URL
                hotel_search_url = f"https://www.google.com/search?q={quote(hotel_name)}+book+hotel"
                for brand, url in HOTEL_BRAND_URLS.items():
                    if brand.lower() in hotel_name.lower():
                        hotel_search_url = url
                        break

                hotels.append({
                    "hotel_id": hotel.get("hotelId"),
                    "name": hotel_name,
                    "rating": hotel.get("rating", "N/A"),
                    "address": hotel.get("address", {}),
                    "price": {
                        "total": best_offer.get("price", {}).get("total", "N/A"),
                        "currency": best_offer.get("price", {}).get("currency", "USD"),
                    },
                    "room_type": best_offer.get("room", {}).get("typeEstimated", {}).get("category", "Standard"),
                    "board_type": best_offer.get("boardType", "ROOM_ONLY"),
                    "cancellation": "Free cancellation" if best_offer.get("policies", {}).get("cancellations") else "Non-refundable",
                    "booking_link": hotel_search_url,
                })

        # Generate search links for the overall search
        search_links = {
            "google_hotels": _get_google_hotels_url(city_code, check_in_date, check_out_date),
            "booking_com": _get_booking_com_url(city_code, check_in_date, check_out_date, adults),
            "hotels_com": _get_hotels_com_url(city_code, check_in_date, check_out_date),
        }

        return {
            "success": True,
            "count": len(hotels),
            "hotels": hotels,
            "search_links": search_links,
            "citation": "⚠️ Prices are ESTIMATES from Amadeus test data - verify on booking sites for actual rates.",
        }

    except ResponseError as e:
        logger.error(f"Amadeus hotel search error: {e.response.body}")
        return {
            "error": f"Amadeus API error: {e.response.body}",
            "success": False,
        }
    except Exception as e:
        logger.error(f"Hotel search error: {str(e)}")
        return {
            "error": f"Error searching hotels: {str(e)}",
            "success": False,
        }


def get_airport_code(city_name: str) -> dict:
    """
    Look up airport IATA code for a city.

    Args:
        city_name: Name of the city (e.g., "San Francisco", "New York")

    Returns:
        Dictionary with airport codes or error message
    """
    client = get_amadeus_client()

    if not client:
        return {
            "error": "Amadeus API not configured.",
        }

    try:
        response = client.reference_data.locations.get(
            keyword=city_name,
            subType="AIRPORT,CITY",
        )

        locations = []
        for loc in response.data[:5]:
            locations.append({
                "name": loc.get("name"),
                "iata_code": loc.get("iataCode"),
                "type": loc.get("subType"),
                "city": loc.get("address", {}).get("cityName", ""),
                "country": loc.get("address", {}).get("countryName", ""),
            })

        return {
            "success": True,
            "locations": locations,
        }

    except ResponseError as e:
        logger.error(f"Amadeus airport lookup error: {e.response.body}")
        return {
            "error": f"Amadeus API error: {e.response.body}",
            "success": False,
        }
    except Exception as e:
        logger.error(f"Airport lookup error: {str(e)}")
        return {
            "error": f"Error looking up location: {str(e)}",
            "success": False,
        }
