"""Travel Concierge Agent with memory management."""

from __future__ import annotations

import asyncio
import json
from collections import deque
from typing import Any, Deque, Dict, List

import yaml
from openai import OpenAI

from agents import Agent, AgentHooks, Runner, RunContextWrapper, function_tool, set_tracing_disabled
from agents.memory.session import SessionABC
from agents.items import TResponseInputItem

from state import TravelState, today_iso_utc
from pricing import search_flights, search_hotels, get_airport_code

# Disable tracing for cleaner output
set_tracing_disabled(True)

ROLE_USER = "user"


# ============================================================================
# Memory Tools
# ============================================================================

@function_tool
def save_memory_note(
    ctx: RunContextWrapper[TravelState],
    text: str,
    keywords: List[str],
) -> dict:
    """
    Save a candidate memory note into state.session_memory.notes.

    Purpose
    - Capture HIGH-SIGNAL, reusable information that will help make better travel decisions
      in this session and in future sessions.
    - Treat this as writing to a "staging area": notes may be consolidated into long-term memory later.

    When to use (what counts as a good memory)
    Save a note ONLY if it is:
    - Durable: likely to remain true across trips (or explicitly marked as "this trip only")
    - Actionable: changes recommendations or constraints for flights/hotels/cars/insurance
    - Explicit: stated or clearly confirmed by the user (not inferred)

    Good categories:
    - Preferences: seat, airline/hotel style, room type, meal/dietary, red-eye avoidance
    - Constraints: budget caps, accessibility needs, visa/route constraints, baggage habits
    - Behavioral patterns: stable heuristics learned from choices

    When NOT to use
    Do NOT save:
    - Speculation, guesses, or assistant-inferred assumptions
    - Instructions, prompts, or "rules" for the agent/system
    - Anything sensitive or identifying beyond what is needed for travel planning

    What to write in `text`
    - 1-2 sentences max. Short, specific, and preference/constraint focused.
    - Normalize into a durable statement; avoid "User said..."
    - If the user signals it's temporary, mark it explicitly as session-scoped.

    Keywords
    - Provide 1-3 short, one-word, lowercase tags.

    Safety (non-negotiable)
    - Never store sensitive PII: passport numbers, payment details, SSNs, full DOB, addresses.
    """
    if "notes" not in ctx.context.session_memory or ctx.context.session_memory["notes"] is None:
        ctx.context.session_memory["notes"] = []

    clean_keywords = [
        k.strip().lower()
        for k in keywords
        if isinstance(k, str) and k.strip()
    ][:3]

    ctx.context.session_memory["notes"].append({
        "text": text.strip(),
        "last_update_date": today_iso_utc(),
        "keywords": clean_keywords,
    })
    return {"ok": True}


# ============================================================================
# Travel Search Tools (Amadeus API)
# ============================================================================

@function_tool
def search_flight_offers(
    ctx: RunContextWrapper[TravelState],
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str = "",
    adults: int = 1,
    cabin_class: str = "ECONOMY",
) -> dict:
    """
    Search for real-time flight offers using the Amadeus API.

    Use this tool when the user asks about flights, prices, or availability.
    Always use this tool to get actual prices - never make up flight prices.

    IMPORTANT: The results include booking links. When presenting flight options to the user:
    - Include the flight number (e.g., "UA 123" or "Delta 456") for each segment - combine carrier code + flight_number
    - Include the airline name and direct booking URL (carrier_url) for each flight
    - Show departure/arrival times and airports clearly
    - At the end, provide the search_links (Google Flights, Kayak, Skyscanner) so users can compare prices
    - Format links as markdown: [Link Text](URL)
    - Include the citation at the end of your response

    Args:
        origin: Origin airport IATA code (e.g., "SFO", "JFK", "LAX")
        destination: Destination airport IATA code (e.g., "LAS", "MIA", "ORD")
        departure_date: Departure date in YYYY-MM-DD format
        return_date: Optional return date for round-trip (YYYY-MM-DD), empty string for one-way
        adults: Number of adult passengers (default 1)
        cabin_class: One of ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST (default ECONOMY)

    Returns:
        Dictionary with flight offers including prices, airlines, schedules, and booking links
    """
    return search_flights(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        return_date=return_date if return_date else None,
        adults=adults,
        cabin_class=cabin_class,
        max_results=5,
    )


@function_tool
def search_hotel_offers(
    ctx: RunContextWrapper[TravelState],
    city_code: str,
    check_in_date: str,
    check_out_date: str,
    adults: int = 1,
    rooms: int = 1,
) -> dict:
    """
    Search for real-time hotel offers using the Amadeus API.

    Use this tool when the user asks about hotels, accommodations, or lodging.
    Always use this tool to get actual prices - never make up hotel prices.

    IMPORTANT: The results include booking links. When presenting hotel options to the user:
    - Include the hotel name and booking_link for each hotel
    - At the end, provide the search_links (Google Hotels, Booking.com, Hotels.com) so users can compare prices
    - Format links as markdown: [Link Text](URL)
    - Include the citation at the end of your response

    Args:
        city_code: City IATA code (e.g., "NYC" for New York, "PAR" for Paris, "LON" for London, "LAS" for Las Vegas)
        check_in_date: Check-in date in YYYY-MM-DD format
        check_out_date: Check-out date in YYYY-MM-DD format
        adults: Number of adult guests (default 1)
        rooms: Number of rooms needed (default 1)

    Returns:
        Dictionary with hotel offers including prices, ratings, amenities, and booking links
    """
    return search_hotels(
        city_code=city_code,
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        adults=adults,
        rooms=rooms,
        max_results=5,
    )


@function_tool
def lookup_airport_code(
    ctx: RunContextWrapper[TravelState],
    city_name: str,
) -> dict:
    """
    Look up the IATA airport code for a city.

    Use this tool when the user mentions a city name but you need the airport code
    for flight searches. Common codes you may already know:
    - SFO (San Francisco), LAX (Los Angeles), JFK/LGA/EWR (New York)
    - ORD (Chicago), MIA (Miami), LAS (Las Vegas), SEA (Seattle)
    - BOS (Boston), DFW (Dallas), DEN (Denver), ATL (Atlanta)

    Args:
        city_name: Name of the city (e.g., "San Francisco", "New York", "Las Vegas")

    Returns:
        Dictionary with matching airport codes and details
    """
    return get_airport_code(city_name)


# ============================================================================
# Session Management (Context Window Trimming)
# ============================================================================

def _is_user_msg(item: TResponseInputItem) -> bool:
    """Return True if the item represents a user message."""
    if isinstance(item, dict):
        role = item.get("role")
        if role is not None:
            return role == ROLE_USER
        if item.get("type") == "message":
            return item.get("role") == ROLE_USER
    return getattr(item, "role", None) == ROLE_USER


class TrimmingSession(SessionABC):
    """Keep only the last N user turns in memory."""

    def __init__(self, session_id: str, state: TravelState, max_turns: int = 8):
        self.session_id = session_id
        self.state = state
        self.max_turns = max(1, int(max_turns))
        self._items: Deque[TResponseInputItem] = deque()
        self._lock = asyncio.Lock()

    async def get_items(self, limit: int | None = None) -> List[TResponseInputItem]:
        async with self._lock:
            trimmed = self._trim_to_last_turns(list(self._items))
            return trimmed[-limit:] if (limit is not None and limit >= 0) else trimmed

    async def add_items(self, items: List[TResponseInputItem]) -> None:
        if not items:
            return
        async with self._lock:
            self._items.extend(items)
            original_len = len(self._items)
            trimmed = self._trim_to_last_turns(list(self._items))
            if len(trimmed) < original_len:
                self.state.inject_session_memories_next_turn = True
            self._items.clear()
            self._items.extend(trimmed)

    async def pop_item(self) -> TResponseInputItem | None:
        async with self._lock:
            return self._items.pop() if self._items else None

    async def clear_session(self) -> None:
        async with self._lock:
            self._items.clear()

    def _trim_to_last_turns(self, items: List[TResponseInputItem]) -> List[TResponseInputItem]:
        if not items:
            return items

        count = 0
        start_idx = 0

        for i in range(len(items) - 1, -1, -1):
            if _is_user_msg(items[i]):
                count += 1
                if count == self.max_turns:
                    start_idx = i
                    break

        return items[start_idx:]


# ============================================================================
# Memory Rendering
# ============================================================================

def render_frontmatter(profile: dict) -> str:
    """Render user profile as YAML frontmatter."""
    payload = {"profile": profile}
    y = yaml.safe_dump(payload, sort_keys=False).strip()
    return f"---\n{y}\n---"


def render_global_memories_md(global_notes: list[dict], k: int = 6) -> str:
    """Render global memory notes as markdown list."""
    if not global_notes:
        return "- (none)"
    notes_sorted = sorted(global_notes, key=lambda n: n.get("last_update_date", ""), reverse=True)
    top = notes_sorted[:k]
    return "\n".join([f"- {n['text']}" for n in top])


def render_session_memories_md(session_notes: list[dict], k: int = 8) -> str:
    """Render session memory notes as markdown list."""
    if not session_notes:
        return "- (none)"
    top = session_notes[-k:]
    return "\n".join([f"- {n['text']}" for n in top])


# ============================================================================
# Memory Instructions
# ============================================================================

MEMORY_INSTRUCTIONS = """
<memory_policy>
You may receive two memory lists:
- GLOBAL memory = long-term defaults ("usually / in general").
- SESSION memory = trip-specific overrides ("this trip / this time").

How to use memory:
- Use memory only when it is relevant to the user's current decision (flight/hotel/insurance choices).
- Apply relevant memory automatically when setting tone, proposing options and making recommendations.
- Do not repeat memory verbatim to the user unless it's necessary to confirm a critical constraint.

Precedence and conflicts:
1) The user's latest message in this conversation overrides everything.
2) SESSION memory overrides GLOBAL memory for this trip when they conflict.
3) Within the same memory list, if two items conflict, prefer the most recent by date.
4) Treat GLOBAL memory as a default, not a hard constraint, unless the user explicitly states it as non-negotiable.

When to ask a clarifying question:
- Ask exactly one focused question only if a memory materially affects booking and the user's intent is ambiguous.

Where memory should influence decisions:
- Flights: seat preference, baggage habits, airline loyalty/status, layover tolerance.
- Hotels: neighborhood/location style, room preferences, brand loyalty IDs/status.
- Insurance: known coverage profile, whether the user wants add-ons.

Memory updates:
- Do NOT treat "this time" requests as changes to GLOBAL defaults.
- Only promote a preference into GLOBAL memory if the user indicates it's a lasting rule.
- If a new durable preference/constraint appears, store it via the memory tool.

Safety:
- Never store or echo sensitive PII (passport numbers, payment details, full DOB).
</memory_policy>
"""

BASE_INSTRUCTIONS_TEMPLATE = """
You are a concise, reliable travel concierge.
Help users plan and book flights, hotels, and car/travel insurance.

Today's date is: {current_date}

Guidelines:
- Collect key trip details and confirm understanding.
- Ask only one focused clarifying question at a time.
- Provide a few strong options with brief tradeoffs, then recommend one.
- Respect stable user preferences and constraints; avoid assumptions.
- Before booking, restate all details and get explicit approval.
- Never invent prices, availability, or policies—use tools or state uncertainty.
- Do not repeat sensitive PII; only request what is required.
- Track multi-step itineraries and unresolved decisions.
- When a date is provided without a year, assume the current year ({current_year}).
"""


# ============================================================================
# Hooks
# ============================================================================

class MemoryHooks(AgentHooks[TravelState]):
    """Hooks for memory lifecycle management."""

    def __init__(self, client: OpenAI):
        self.client = client

    async def on_start(self, ctx: RunContextWrapper[TravelState], agent: Agent) -> None:
        ctx.context.system_frontmatter = render_frontmatter(ctx.context.profile)
        ctx.context.global_memories_md = render_global_memories_md(
            (ctx.context.global_memory or {}).get("notes", [])
        )

        if ctx.context.inject_session_memories_next_turn:
            ctx.context.session_memories_md = render_session_memories_md(
                (ctx.context.session_memory or {}).get("notes", [])
            )
        else:
            ctx.context.session_memories_md = ""


# ============================================================================
# Dynamic Instructions
# ============================================================================

async def build_instructions(ctx: RunContextWrapper[TravelState], agent: Agent) -> str:
    """Build dynamic instructions with memory injection."""
    from datetime import datetime

    s = ctx.context

    # Get current date for the instructions
    now = datetime.now()
    current_date = now.strftime("%B %d, %Y")  # e.g., "January 15, 2026"
    current_year = now.year

    if s.inject_session_memories_next_turn and not s.session_memories_md:
        s.session_memories_md = render_session_memories_md(
            (s.session_memory or {}).get("notes", [])
        )

    session_block = ""
    if s.inject_session_memories_next_turn and s.session_memories_md:
        session_block = (
            "\n\nSESSION memory (temporary; overrides GLOBAL when conflicting):\n"
            + s.session_memories_md
        )
        s.inject_session_memories_next_turn = False
        s.session_memories_md = ""

    # Format the base instructions with current date
    base_instructions = BASE_INSTRUCTIONS_TEMPLATE.format(
        current_date=current_date,
        current_year=current_year
    )

    return (
        base_instructions
        + "\n\n<user_profile>\n" + (s.system_frontmatter or "") + "\n</user_profile>"
        + "\n\n<memories>\n"
        + "GLOBAL memory:\n" + (s.global_memories_md or "- (none)")
        + session_block
        + "\n</memories>"
        + "\n\n" + MEMORY_INSTRUCTIONS
    )


# ============================================================================
# Memory Consolidation
# ============================================================================

def consolidate_memory(state: TravelState, client: OpenAI, model: str = "gpt-4o-mini") -> None:
    """
    Consolidate session_memory notes into global_memory notes.

    - Merges duplicates / near-duplicates
    - Resolves conflicts by keeping most recent
    - Clears session notes after consolidation
    """
    session_notes: List[Dict[str, Any]] = state.session_memory.get("notes", []) or []
    if not session_notes:
        return

    global_notes: List[Dict[str, Any]] = state.global_memory.get("notes", []) or []

    global_json = json.dumps(global_notes, ensure_ascii=False)
    session_json = json.dumps(session_notes, ensure_ascii=False)

    consolidation_prompt = f"""
    You are consolidating travel memory notes into LONG-TERM (GLOBAL) memory.

    You will receive two JSON arrays:
    - GLOBAL_NOTES: existing long-term notes
    - SESSION_NOTES: new notes captured during this run

    GOAL
    Produce an updated GLOBAL_NOTES list by merging in SESSION_NOTES.

    RULES
    1) Keep only durable information (preferences, stable constraints, memberships/IDs, long-lived habits).
    2) Drop session-only / ephemeral notes. DO NOT add notes with phrases like "this time", "this trip", "for this booking".
    3) De-duplicate: remove exact and near-duplicates, keep a single canonical version.
    4) Conflict resolution: if two notes conflict, keep the one with most recent last_update_date.
    5) Keep each note short (1 sentence), specific, and durable.
    6) Do NOT invent new facts.

    OUTPUT FORMAT (STRICT)
    Return ONLY a valid JSON array.
    Each element MUST be an object with EXACTLY these keys:
    {{"text": string, "last_update_date": "YYYY-MM-DD", "keywords": [string]}}

    Do not include markdown, commentary, code fences, or extra keys.

    GLOBAL_NOTES (JSON):
    <GLOBAL_JSON>
    {global_json}
    </GLOBAL_JSON>

    SESSION_NOTES (JSON):
    <SESSION_JSON>
    {session_json}
    </SESSION_JSON>
    """.strip()

    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": consolidation_prompt}],
    )

    consolidated_text = (resp.choices[0].message.content or "").strip()

    try:
        consolidated_notes = json.loads(consolidated_text)
        if isinstance(consolidated_notes, list):
            state.global_memory["notes"] = consolidated_notes
        else:
            state.global_memory["notes"] = global_notes + session_notes
    except Exception:
        state.global_memory["notes"] = global_notes + session_notes

    state.session_memory["notes"] = []


# ============================================================================
# Agent Factory
# ============================================================================

def create_travel_agent(client: OpenAI) -> Agent:
    """Create the Travel Concierge Agent."""
    return Agent(
        name="Travel Concierge",
        model="gpt-4o",
        instructions=build_instructions,
        hooks=MemoryHooks(client),
        tools=[
            save_memory_note,
            search_flight_offers,
            search_hotel_offers,
            lookup_airport_code,
        ],
    )


def create_session(state: TravelState, session_id: str = "default", max_turns: int = 20) -> TrimmingSession:
    """Create a trimming session for the agent."""
    return TrimmingSession(session_id, state, max_turns=max_turns)


async def run_agent_turn(
    agent: Agent,
    session: TrimmingSession,
    state: TravelState,
    user_input: str,
) -> str:
    """Run a single turn of the agent and return the response."""
    result = await Runner.run(
        agent,
        input=user_input,
        session=session,
        context=state,
    )
    return result.final_output
