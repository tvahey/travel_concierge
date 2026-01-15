# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Travel Concierge Agent - A Streamlit web app that provides personalized travel assistance using OpenAI's Agents SDK with a two-tier memory system (global/session).

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the web app
streamlit run app.py

# Run on specific port
streamlit run app.py --server.port 8501
```

## Architecture

### Memory System

The agent uses a **state-based long-term memory** pattern:

- **Global Memory**: Durable preferences that persist across sessions (e.g., "prefers aisle seats")
- **Session Memory**: Trip-specific or temporary preferences (e.g., "this time wants window seat")
- **Consolidation**: Session notes are promoted to global memory at session end if they represent lasting preferences

Memory precedence (highest to lowest):
1. User's latest message in current conversation
2. Session memory (trip-specific overrides)
3. Global memory (long-term defaults)

### Key Modules

- `app.py` - Streamlit chat interface and session management
- `agent.py` - OpenAI Agents SDK integration, memory tools, dynamic instructions
- `state.py` - `TravelState` dataclass with profile, memories, and trip history
- `storage.py` - JSON file persistence in `data/` directory

### Data Flow

1. User state loaded from `data/{user_id}.json` on session start
2. `MemoryHooks.on_start()` renders profile and memories into system prompt
3. Agent runs with `save_memory_note` tool available for capturing new preferences
4. `TrimmingSession` manages context window (keeps last N user turns)
5. State auto-saved after each turn; manual consolidation via sidebar button

## Environment

Requires `OPENAI_API_KEY` in `.env` file.
