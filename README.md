# HacktheFuture – Automotive Supply Chain Risk Agent

An AI-powered supply chain risk agent for automotive manufacturers. It assesses disruptions, recommends mitigation options, and helps with escalation and supplier communication.

## Features

- **Risk assessment** – Evaluates supply chain disruptions and their impact
- **Signal handling** – Processes disruption signals (delays, supplier issues, etc.)
- **Mitigation options** – Suggests actions with trade-offs
- **Approval boundaries** – Indicates when human approval is required (HITL)
- **Similar past cases** – References historical disruption data (lightweight memory)
- **Business impact (CAD)** – Estimates revenue/margin at risk and compares with vs without agent (scenario-based)

## Setup

### Prerequisites

- Python 3.10+
- A Google AI API key (Gemini)

### Installation

```bash
# Clone the repository
git clone https://github.com/tamiw10/HacktheFuture.git
cd HacktheFuture

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env and add your API key (DO NOT commit .env)
cp multi_tool_agent/.env.example multi_tool_agent/.env
# Edit multi_tool_agent/.env and set: GOOGLE_API_KEY=your-api-key
```

## Running the demo (recommended workflow)

This demo is designed to be reproducible: reset to a clean baseline, simulate disruption signals, then run the agent.

```bash
# Activate venv if not already active
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 1) Reset demo data to a clean baseline
python scripts/reset_demo_data.py

# 2) Simulate disruption signals (creates a fresh scenario)
python -m multi_tool_agent.signal_simulator

# 3) Start ADK Web UI
adk web
```

Open the UI at: http://127.0.0.1:8000

### Optional: SSL fix (only if you see SSL/cert errors)

```bash
export SSL_CERT_FILE=$(python -m certifi)
```

Then rerun:

```bash
adk web
```

## Suggested demo prompts

**Prompt 1 (fragile manufacturer / critical risk):**

> A disruption signal was received for shipment SHIP001. Assess risk for the affected manufacturer. Compare mitigation options, recommend the best immediate action (and why alternatives aren't viable), include a reorder contingency, draft an escalation message, draft a supplier email with an approval note, show human approval boundaries, and mention similar past cases.

**Prompt 2 (resilient manufacturer / lower risk):**

> A disruption signal was received for shipment SHIP002. Assess risk for the affected manufacturer. Recommend the best action and explain why expensive mitigation isn't needed right now. Include reorder guidance, escalation (or none), supplier email with approval note, human approval boundaries, and similar past cases.

## Scripts

- **Initialize baseline data** (run after you intentionally change the clean starting state):
  ```bash
  python scripts/init_baseline.py
  ```

- **Reset demo data** (run before each demo run):
  ```bash
  python scripts/reset_demo_data.py
  ```

## Project structure

```
HacktheFuture/
├── multi_tool_agent/      # Agent definition, tools, perception, metrics
├── data/                  # JSON data (shipments, inventory, suppliers, etc.)
│   └── baseline/          # Clean baseline state for reproducible demos
├── scripts/               # Utility scripts (baseline/reset)
└── requirements.txt
```

## Notes on numbers and explainability

- Time saved and cost premiums for mitigations are scenario-based inputs for the prototype.
- Monetary outputs are presented in CAD using `data/business_parameters.json`.
- The agent drafts escalation and supplier messages but enforces human approval boundaries for external communication and financial actions.

## License

MIT
