"""Streamlit web app for Travel Concierge Agent."""

import asyncio
import os
import traceback

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from agent import create_travel_agent, create_session, run_agent_turn, consolidate_memory
from storage import load_user_state, save_user_state
from state import TravelState
from logger import setup_logging, get_logger, read_logs, read_errors, clear_logs, get_log_stats
from auth import authenticate, create_user, get_user_display_name, ensure_default_user

# Load environment variables (for local development)
load_dotenv()


def get_secret(key: str, default: str = None) -> str:
    """Get secret from Streamlit secrets (cloud) or environment variables (local)."""
    # Try Streamlit secrets first (for Streamlit Cloud)
    try:
        if hasattr(st, 'secrets') and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    # Fall back to environment variables (for local development)
    return os.getenv(key, default)

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Ensure default user exists
ensure_default_user()

# Page config
st.set_page_config(
    page_title="Travel Concierge",
    page_icon="✈️",
    layout="centered",
)


def display_login_page():
    """Display login and registration forms."""
    st.title("✈️ Travel Concierge Agent")
    st.caption("Your personalized travel assistant with long-term memory")

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        st.subheader("Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)

            if submit:
                if authenticate(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username.lower()
                    st.session_state.display_name = get_user_display_name(username)
                    logger.info(f"User logged in: {username}")
                    st.rerun()
                else:
                    st.error("Invalid username or password")

    with tab2:
        st.subheader("Create Account")
        with st.form("register_form"):
            new_username = st.text_input("Username", key="reg_username")
            new_display_name = st.text_input("Display Name (optional)", key="reg_display")
            new_password = st.text_input("Password", type="password", key="reg_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")
            register = st.form_submit_button("Create Account", use_container_width=True)

            if register:
                if new_password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    success, message = create_user(new_username, new_password, new_display_name)
                    if success:
                        st.success(message + " Please login.")
                    else:
                        st.error(message)


def get_openai_client() -> OpenAI:
    """Get or create OpenAI client."""
    api_key = get_secret("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not found")
        st.error("OPENAI_API_KEY not found. Please add it to Streamlit secrets or .env file.")
        st.stop()
    logger.info("OpenAI client initialized")
    return OpenAI(api_key=api_key)


def init_session_state():
    """Initialize Streamlit session state."""
    # Use the authenticated username as user_id
    if "user_id" not in st.session_state:
        st.session_state.user_id = st.session_state.get("username", "default_user")

    # Reset if user changed
    current_user = st.session_state.get("username", "default_user")
    if st.session_state.user_id != current_user:
        st.session_state.user_id = current_user
        # Clear cached state for new user
        if "user_state" in st.session_state:
            del st.session_state.user_state
        if "messages" in st.session_state:
            del st.session_state.messages
        if "session" in st.session_state:
            del st.session_state.session

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "user_state" not in st.session_state:
        st.session_state.user_state = load_user_state(st.session_state.user_id)

    if "client" not in st.session_state:
        st.session_state.client = get_openai_client()

    if "agent" not in st.session_state:
        st.session_state.agent = create_travel_agent(st.session_state.client)

    if "session" not in st.session_state:
        st.session_state.session = create_session(
            st.session_state.user_state,
            session_id=st.session_state.user_id,
        )


def run_async(coro):
    """Run async function in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def display_sidebar():
    """Display sidebar with user profile and memory info."""
    with st.sidebar:
        # User account info and logout
        col1, col2 = st.columns([3, 1])
        with col1:
            display_name = st.session_state.get("display_name", "User")
            st.write(f"👋 **{display_name}**")
        with col2:
            if st.button("Logout", key="logout_btn"):
                # Clear session state
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                logger.info(f"User logged out: {display_name}")
                st.rerun()

        st.divider()

        st.header("👤 User Profile")

        user_state: TravelState = st.session_state.user_state
        profile = user_state.profile

        st.write(f"**Name:** {profile.get('name', 'N/A')}")
        st.write(f"**Home City:** {profile.get('home_city', 'N/A')}")

        # Show key preferences summary
        flight_prefs = profile.get("flight_preferences", {})
        if flight_prefs.get("home_airport"):
            st.write(f"**Home Airport:** {flight_prefs.get('home_airport')}")

        # Show active loyalty programs
        ff_programs = profile.get("frequent_flyer_programs", [])
        active_ff = [p for p in ff_programs if p.get("active")]
        if active_ff:
            st.write("**Active Airline Program:**")
            for p in active_ff:
                st.write(f"  ✈️ {p['program']} - {p['status']}")

        hotel_programs = profile.get("hotel_loyalty_programs", [])
        active_hotel = [p for p in hotel_programs if p.get("active")]
        if active_hotel:
            st.write("**Active Hotel Program:**")
            for p in active_hotel:
                st.write(f"  🏨 {p['program']} - {p['status']}")

        # Edit Profile Section
        with st.expander("✏️ Edit Profile", expanded=False):
            with st.form("profile_form"):
                new_name = st.text_input("Name", value=profile.get("name", ""))
                new_home_city = st.text_input("Home City", value=profile.get("home_city", ""))
                new_currency = st.selectbox(
                    "Currency",
                    options=["USD", "EUR", "GBP", "CAD", "AUD", "JPY"],
                    index=["USD", "EUR", "GBP", "CAD", "AUD", "JPY"].index(profile.get("currency", "USD")) if profile.get("currency", "USD") in ["USD", "EUR", "GBP", "CAD", "AUD", "JPY"] else 0
                )
                new_tone = st.selectbox(
                    "Communication Tone",
                    options=["concise and friendly", "detailed and formal", "casual"],
                    index=0
                )

                if st.form_submit_button("Save Profile"):
                    profile["name"] = new_name
                    profile["home_city"] = new_home_city
                    profile["currency"] = new_currency
                    profile["tone"] = new_tone
                    save_user_state(st.session_state.user_id, st.session_state.user_state)
                    st.success("Profile saved!")
                    st.rerun()

        # Flight Preferences Section
        flight_prefs = profile.get("flight_preferences", {})
        with st.expander("✈️ Flight Preferences", expanded=False):
            with st.form("flight_prefs_form"):
                new_home_airport = st.text_input(
                    "Home Airport (IATA code)",
                    value=flight_prefs.get("home_airport", ""),
                    placeholder="e.g., SFO, JFK, LAX"
                )
                new_seat = st.selectbox(
                    "Seat Preference",
                    options=["aisle", "window", "middle"],
                    index=["aisle", "window", "middle"].index(flight_prefs.get("seat_preference", "aisle")) if flight_prefs.get("seat_preference", "aisle") in ["aisle", "window", "middle"] else 0
                )
                new_departure_time = st.selectbox(
                    "Preferred Departure Time",
                    options=["morning", "afternoon", "evening", "no preference"],
                    index=["morning", "afternoon", "evening", "no preference"].index(flight_prefs.get("departure_time", "morning")) if flight_prefs.get("departure_time", "morning") in ["morning", "afternoon", "evening", "no preference"] else 0
                )
                new_cabin = st.selectbox(
                    "Cabin Class",
                    options=["economy", "premium_economy", "business", "first"],
                    index=["economy", "premium_economy", "business", "first"].index(flight_prefs.get("cabin_class", "economy")) if flight_prefs.get("cabin_class", "economy") in ["economy", "premium_economy", "business", "first"] else 0
                )
                new_max_layovers = st.selectbox(
                    "Maximum Layovers",
                    options=[0, 1, 2, 3],
                    index=flight_prefs.get("max_layovers", 1) if flight_prefs.get("max_layovers", 1) in [0, 1, 2, 3] else 1
                )
                new_avoid_red_eye = st.checkbox(
                    "Avoid Red-Eye Flights",
                    value=flight_prefs.get("avoid_red_eye", True)
                )

                if st.form_submit_button("Save Flight Preferences"):
                    profile["flight_preferences"] = {
                        "home_airport": new_home_airport.upper().strip(),
                        "seat_preference": new_seat,
                        "departure_time": new_departure_time,
                        "cabin_class": new_cabin,
                        "max_layovers": new_max_layovers,
                        "avoid_red_eye": new_avoid_red_eye,
                    }
                    save_user_state(st.session_state.user_id, st.session_state.user_state)
                    st.success("Flight preferences saved!")
                    st.rerun()

        # Hotel Preferences Section
        hotel_prefs = profile.get("hotel_preferences", {})
        with st.expander("🏨 Hotel Preferences", expanded=False):
            with st.form("hotel_prefs_form"):
                # Preferred brands as comma-separated
                current_brands = ", ".join(hotel_prefs.get("preferred_brands", []))
                new_brands_str = st.text_input(
                    "Preferred Brands (comma-separated)",
                    value=current_brands,
                    placeholder="e.g., Marriott, Hilton, Hyatt"
                )
                new_min_stars = st.selectbox(
                    "Minimum Stars",
                    options=[1, 2, 3, 4, 5],
                    index=hotel_prefs.get("min_stars", 4) - 1 if hotel_prefs.get("min_stars", 4) in [1, 2, 3, 4, 5] else 3
                )
                new_hotel_on_airport = st.checkbox(
                    "Prefer On-Airport Hotels",
                    value=hotel_prefs.get("on_airport", False)
                )
                new_high_floor = st.checkbox(
                    "Prefer High Floor",
                    value=hotel_prefs.get("prefer_high_floor", True)
                )
                new_bed_type = st.selectbox(
                    "Bed Type",
                    options=["king", "queen", "double", "twin", "no preference"],
                    index=["king", "queen", "double", "twin", "no preference"].index(hotel_prefs.get("bed_type", "king")) if hotel_prefs.get("bed_type", "king") in ["king", "queen", "double", "twin", "no preference"] else 0
                )
                new_smoking = st.checkbox(
                    "Smoking Room",
                    value=hotel_prefs.get("smoking", False)
                )

                if st.form_submit_button("Save Hotel Preferences"):
                    # Parse brands
                    new_brands = [b.strip() for b in new_brands_str.split(",") if b.strip()]
                    profile["hotel_preferences"] = {
                        "preferred_brands": new_brands,
                        "min_stars": new_min_stars,
                        "on_airport": new_hotel_on_airport,
                        "prefer_high_floor": new_high_floor,
                        "bed_type": new_bed_type,
                        "smoking": new_smoking,
                    }
                    save_user_state(st.session_state.user_id, st.session_state.user_state)
                    st.success("Hotel preferences saved!")
                    st.rerun()

        # Car Rental Preferences Section
        car_prefs = profile.get("car_preferences", {})
        with st.expander("🚗 Car Rental Preferences", expanded=False):
            with st.form("car_prefs_form"):
                new_car_size = st.selectbox(
                    "Preferred Size",
                    options=["compact", "midsize", "full-size", "suv", "luxury", "minivan"],
                    index=["compact", "midsize", "full-size", "suv", "luxury", "minivan"].index(car_prefs.get("preferred_size", "midsize")) if car_prefs.get("preferred_size", "midsize") in ["compact", "midsize", "full-size", "suv", "luxury", "minivan"] else 1
                )
                new_car_on_airport = st.checkbox(
                    "Prefer On-Airport Pickup",
                    value=car_prefs.get("on_airport", True)
                )
                # Preferred companies as comma-separated
                current_companies = ", ".join(car_prefs.get("preferred_companies", []))
                new_companies_str = st.text_input(
                    "Preferred Companies (comma-separated)",
                    value=current_companies,
                    placeholder="e.g., Enterprise, Hertz, National"
                )

                if st.form_submit_button("Save Car Preferences"):
                    # Parse companies
                    new_companies = [c.strip() for c in new_companies_str.split(",") if c.strip()]
                    profile["car_preferences"] = {
                        "preferred_size": new_car_size,
                        "on_airport": new_car_on_airport,
                        "preferred_companies": new_companies,
                    }
                    save_user_state(st.session_state.user_id, st.session_state.user_state)
                    st.success("Car preferences saved!")
                    st.rerun()

        # Frequent Flyer Programs
        with st.expander(f"✈️ Frequent Flyer Programs ({len(ff_programs)})", expanded=False):
            if ff_programs:
                for i, prog in enumerate(ff_programs):
                    col1, col2, col3 = st.columns([1, 3, 1])
                    with col1:
                        new_active = st.checkbox(
                            "Active",
                            value=prog.get("active", False),
                            key=f"ff_active_{i}",
                            label_visibility="collapsed"
                        )
                        if new_active != prog.get("active", False):
                            prog["active"] = new_active
                            save_user_state(st.session_state.user_id, st.session_state.user_state)
                            st.rerun()
                    with col2:
                        st.write(f"**{prog['program']}**")
                        st.caption(f"{prog.get('status', 'Member')} · {prog.get('member_id', '')}")
                    with col3:
                        if st.button("🗑️", key=f"del_ff_{i}"):
                            ff_programs.pop(i)
                            save_user_state(st.session_state.user_id, st.session_state.user_state)
                            st.rerun()
            else:
                st.write("No frequent flyer programs added.")

            st.divider()
            st.write("**Add New Program:**")
            with st.form("add_ff_form"):
                new_ff_program = st.text_input("Program Name", placeholder="e.g., United MileagePlus")
                new_ff_id = st.text_input("Member ID", placeholder="e.g., AB123456")
                new_ff_status = st.text_input("Status", placeholder="e.g., Gold, Platinum")
                if st.form_submit_button("➕ Add Program"):
                    if new_ff_program.strip():
                        ff_programs.append({
                            "program": new_ff_program.strip(),
                            "member_id": new_ff_id.strip(),
                            "status": new_ff_status.strip() or "Member",
                            "active": False
                        })
                        profile["frequent_flyer_programs"] = ff_programs
                        save_user_state(st.session_state.user_id, st.session_state.user_state)
                        st.rerun()

        # Hotel Loyalty Programs
        with st.expander(f"🏨 Hotel Loyalty Programs ({len(hotel_programs)})", expanded=False):
            if hotel_programs:
                for i, prog in enumerate(hotel_programs):
                    col1, col2, col3 = st.columns([1, 3, 1])
                    with col1:
                        new_active = st.checkbox(
                            "Active",
                            value=prog.get("active", False),
                            key=f"hotel_active_{i}",
                            label_visibility="collapsed"
                        )
                        if new_active != prog.get("active", False):
                            prog["active"] = new_active
                            save_user_state(st.session_state.user_id, st.session_state.user_state)
                            st.rerun()
                    with col2:
                        st.write(f"**{prog['program']}**")
                        st.caption(f"{prog.get('status', 'Member')} · {prog.get('member_id', '')}")
                    with col3:
                        if st.button("🗑️", key=f"del_hotel_{i}"):
                            hotel_programs.pop(i)
                            save_user_state(st.session_state.user_id, st.session_state.user_state)
                            st.rerun()
            else:
                st.write("No hotel loyalty programs added.")

            st.divider()
            st.write("**Add New Program:**")
            with st.form("add_hotel_form"):
                new_hotel_program = st.text_input("Program Name", placeholder="e.g., Marriott Bonvoy")
                new_hotel_id = st.text_input("Member ID", placeholder="e.g., MR998877")
                new_hotel_status = st.text_input("Status", placeholder="e.g., Gold, Titanium")
                if st.form_submit_button("➕ Add Program"):
                    if new_hotel_program.strip():
                        hotel_programs.append({
                            "program": new_hotel_program.strip(),
                            "member_id": new_hotel_id.strip(),
                            "status": new_hotel_status.strip() or "Member",
                            "active": False
                        })
                        profile["hotel_loyalty_programs"] = hotel_programs
                        save_user_state(st.session_state.user_id, st.session_state.user_state)
                        st.rerun()

        st.divider()

        st.header("🧠 Memory")

        global_notes = user_state.global_memory.get("notes", [])
        session_notes = user_state.session_memory.get("notes", [])

        # Global Memory with edit/delete
        with st.expander(f"Global Memory ({len(global_notes)} notes)", expanded=False):
            if global_notes:
                for i, note in enumerate(global_notes):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.write(f"• {note.get('text', '')}")
                    with col2:
                        if st.button("🗑️", key=f"del_global_{i}", help="Delete this memory"):
                            global_notes.pop(i)
                            save_user_state(st.session_state.user_id, st.session_state.user_state)
                            st.rerun()
            else:
                st.write("No global memories yet.")

            # Add new global memory
            st.divider()
            new_memory = st.text_input("Add new memory:", key="new_global_memory", placeholder="e.g., Prefers vegetarian meals")
            if st.button("➕ Add", key="add_global"):
                if new_memory.strip():
                    from state import today_iso_utc
                    global_notes.append({
                        "text": new_memory.strip(),
                        "last_update_date": today_iso_utc(),
                        "keywords": []
                    })
                    save_user_state(st.session_state.user_id, st.session_state.user_state)
                    st.rerun()

        with st.expander(f"Session Memory ({len(session_notes)} notes)", expanded=False):
            if session_notes:
                for i, note in enumerate(session_notes):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.write(f"• {note.get('text', '')}")
                    with col2:
                        if st.button("🗑️", key=f"del_session_{i}", help="Delete this memory"):
                            session_notes.pop(i)
                            save_user_state(st.session_state.user_id, st.session_state.user_state)
                            st.rerun()
            else:
                st.write("No session memories yet.")

        st.divider()

        col1, col2 = st.columns(2)

        with col1:
            if st.button("💾 Save", help="Save current state to disk"):
                save_user_state(st.session_state.user_id, st.session_state.user_state)
                st.success("Saved!")

        with col2:
            if st.button("🔄 Consolidate", help="Consolidate session memories into global"):
                consolidate_memory(
                    st.session_state.user_state,
                    st.session_state.client,
                )
                save_user_state(st.session_state.user_id, st.session_state.user_state)
                st.success("Consolidated!")
                st.rerun()

        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.session = create_session(
                st.session_state.user_state,
                session_id=st.session_state.user_id,
            )
            logger.info("Chat cleared by user")
            st.rerun()

        st.divider()

        # Admin Section
        st.header("⚙️ Admin")

        log_stats = get_log_stats()

        # Show error/warning count
        if log_stats.get("exists"):
            error_count = log_stats.get("errors", 0)
            warning_count = log_stats.get("warnings", 0)

            if error_count > 0 or warning_count > 0:
                st.warning(f"⚠️ {error_count} errors, {warning_count} warnings")
            else:
                st.success("✅ No errors")

            st.caption(f"Log size: {log_stats.get('size_kb', 0)} KB")

        # View Logs
        with st.expander("📋 View Logs", expanded=False):
            tab1, tab2 = st.tabs(["Errors Only", "All Logs"])

            with tab1:
                errors = read_errors(50)
                st.code(errors, language="log")

            with tab2:
                logs = read_logs(100)
                st.code(logs, language="log")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Refresh Logs"):
                    st.rerun()
            with col2:
                if st.button("🗑️ Clear Logs"):
                    clear_logs()
                    logger.info("Logs cleared by user")
                    st.success("Logs cleared!")
                    st.rerun()

        # API Status
        with st.expander("🔌 API Status", expanded=False):
            openai_key = os.getenv("OPENAI_API_KEY")
            amadeus_key = os.getenv("AMADEUS_API_KEY")
            amadeus_secret = os.getenv("AMADEUS_API_SECRET")

            st.write("**OpenAI API:**", "✅ Configured" if openai_key else "❌ Missing")
            st.write("**Amadeus API:**", "✅ Configured" if (amadeus_key and amadeus_secret and "your_" not in amadeus_key) else "❌ Not configured")

            if amadeus_key and amadeus_secret and "your_" not in amadeus_key:
                st.warning("⚠️ **Test Mode**: Prices & times are estimates. Verify on booking sites.")
            else:
                st.caption("Add Amadeus keys to .env for real-time pricing")


def display_chat():
    """Display chat messages and handle input."""
    # Display existing messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask about flights, hotels, or travel plans..."):
        # Add user message to display
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        logger.info(f"User input: {prompt[:100]}...")

        # Get agent response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = run_async(
                        run_agent_turn(
                            st.session_state.agent,
                            st.session_state.session,
                            st.session_state.user_state,
                            prompt,
                        )
                    )
                    logger.info(f"Agent response received ({len(response)} chars)")
                except Exception as e:
                    error_msg = f"Error getting agent response: {str(e)}"
                    logger.error(error_msg)
                    logger.error(traceback.format_exc())
                    response = f"Sorry, I encountered an error: {str(e)}"
                    st.error(response)

            st.markdown(response)

        # Add assistant message to display
        st.session_state.messages.append({"role": "assistant", "content": response})

        # Auto-save state after each turn
        try:
            save_user_state(st.session_state.user_id, st.session_state.user_state)
        except Exception as e:
            logger.error(f"Error saving user state: {str(e)}")


def display_main_app():
    """Display the main app (after authentication)."""
    st.title("✈️ Travel Concierge Agent")
    st.caption("Your personalized travel assistant with long-term memory")

    # Pricing disclaimer
    st.info("💡 **Note:** Flight/hotel prices and times are estimates. Use the booking links to verify actual rates.", icon="ℹ️")

    init_session_state()
    display_sidebar()
    display_chat()


def main():
    """Main app entry point."""
    # Check if user is authenticated
    if not st.session_state.get("authenticated", False):
        display_login_page()
    else:
        display_main_app()


if __name__ == "__main__":
    main()
