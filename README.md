# Travel Concierge Agent

A personalized travel assistant web app with long-term memory, built with Streamlit and OpenAI's Agents SDK.

## Features

- **Conversational Travel Planning** - Chat with an AI agent to plan flights, hotels, and trips
- **Real-Time Pricing** - Search actual flight and hotel prices via Amadeus API
- **Two-Tier Memory System**
  - **Global Memory** - Long-term preferences that persist across sessions
  - **Session Memory** - Trip-specific preferences for the current conversation
- **Memory Consolidation** - Automatically promotes durable preferences to long-term memory
- **User Profile Management** - Edit your preferences, loyalty programs, and travel settings
- **Multiple Loyalty Programs** - Add multiple frequent flyer and hotel programs with active toggles

## Quick Start

### 1. Clone and Setup

```bash
# Run the setup script (creates venv, installs dependencies, starts app)
./setup.sh
```

Or manually:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

### 2. Configure API Keys

Edit the `.env` file with your API keys:

```bash
# Required - Get from https://platform.openai.com
OPENAI_API_KEY=your_openai_api_key

# Optional - Get free keys from https://developers.amadeus.com
AMADEUS_API_KEY=your_amadeus_api_key
AMADEUS_API_SECRET=your_amadeus_api_secret
```

### 3. Open the App

Navigate to http://localhost:8501 in your browser.

## Usage

### Chat with the Agent

Ask questions like:
- "Book me a flight from SFO to Las Vegas next Friday"
- "Find hotels in Paris for 3 nights"
- "What are my travel preferences?"
- "Remember that I prefer window seats on overnight flights"

### Manage Your Profile

In the sidebar, you can:
- **Edit Profile** - Update name, home city, seat preference, currency
- **Frequent Flyer Programs** - Add/remove airline loyalty programs, toggle which is active
- **Hotel Loyalty Programs** - Add/remove hotel loyalty programs, toggle which is active
- **Global Memory** - View, add, or delete long-term preferences
- **Session Memory** - View current session preferences

### Memory System

The agent automatically learns your preferences during conversation:

1. When you mention a preference ("I'm vegetarian"), the agent saves it to session memory
2. Click **Consolidate** to promote durable preferences to global memory
3. Session-specific preferences ("this time I want a window seat") stay in session memory

## Project Structure

```
├── app.py          # Streamlit web interface
├── agent.py        # OpenAI Agents SDK integration
├── state.py        # TravelState dataclass and defaults
├── storage.py      # JSON file persistence
├── pricing.py      # Amadeus API integration
├── setup.sh        # First-time setup script
├── run.sh          # Run script (after setup)
├── requirements.txt
├── .env            # API keys (not committed)
└── data/           # User state files (JSON)
```

## API Integrations

### OpenAI (Required)
Powers the conversational agent. Get an API key at https://platform.openai.com

### Amadeus (Optional)
Provides real-time flight and hotel pricing. Free tier includes 500 API calls/month.
Sign up at https://developers.amadeus.com

Without Amadeus keys, the agent will still work but cannot fetch real prices.

## Development

```bash
# Activate the virtual environment
source venv/bin/activate

# Run the app
streamlit run app.py

# Run on a different port
streamlit run app.py --server.port 8502
```

## License

MIT
