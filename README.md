# HacktheFuture – Automotive Supply Chain Risk Agent

An AI-powered supply chain risk agent for automotive manufacturers. It assesses disruptions, recommends mitigation options, and helps with escalation and supplier communication.

## Features

- **Risk assessment** – Evaluates supply chain disruptions and their impact
- **Signal handling** – Processes disruption signals (delays, quality issues, etc.)
- **Mitigation options** – Suggests actions with trade-offs
- **Approval boundaries** – Indicates when human approval is required
- **Similar past cases** – References historical disruption data

## Setup

### Prerequisites

- Python 3.10+
- [Google AI API key](https://aistudio.google.com/apikey) (for Gemini)

### Installation

```bash
# Clone the repository
git clone https://github.com/tamiw10/HacktheFuture.git
cd HacktheFuture

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template and add your API key
cp .env.example multi_tool_agent/.env
# Edit multi_tool_agent/.env and set GOOGLE_API_KEY=your-api-key
```

### Running the agent

1. **Simulate disruption signals** (run before prompting):

```bash
source .venv/bin/activate
python scripts/reset_demo_data.py
python -m multi_tool_agent.signal_simulator
```

2. **Start the web UI**:

```bash
export SSL_CERT_FILE=$(python -m certifi)  # Optional: for SSL on some systems
adk web
```

Then open the web UI (typically http://localhost:8000 or as shown in the terminal).

### Scripts

- **Initialize baseline data**: `python scripts/init_baseline.py`
- **Reset demo data**: `python scripts/reset_demo_data.py`

## Project structure

```
HacktheFuture/
├── multi_tool_agent/     # Agent definition and tools
├── data/                 # JSON data (shipments, inventory, suppliers, etc.)
├── scripts/              # Utility scripts
└── requirements.txt
```

## License

MIT
