 # ChainGuard AI — Autonomous Cold-Chain Logistics Control Tower

Built for the **BOB AI Innovation Hackathon** by **Team Chaos**.

---

## Team

- **Track:** AI
- **Team Lead:** Divyaraj Puwar — AI Decision Engine, Architecture, Integration, Pitch
- **Team Members:**
  - Bhakti Hotwani — IoT Telemetry, Temperature Anomaly Logic, Cold-Chain Safety Rules
  - Anjali Patel — Control Tower UI, Data Visualization, Demo Experience
  - Dhairya Jani — FastAPI Backend, Routing Logic, Fleet & Scenario Simulation

---

## Problem Statement

When logistics networks experience sudden macro disruptions—such as harbor strikes or regional corridor shutdowns—cargo risk compounds exponentially. In temperature-sensitive cold-chain logistics, waiting out a bottleneck is fatal: biological pharmaceuticals and vaccines degrade if ambient conditions drift outside strict 2°C to 8°C limits. 

Conventional navigation platforms only discover problems after delays occur and optimize purely for road speed. They completely ignore cargo perishability limits, run-time battery reserves, and nearby idle fleet capacity.

---

## Solution

ChainGuard AI converts real-time supply chain disruptions into autonomous, explainable recovery actions through a closed five-step operational loop:

1. **Detect:** Real-time ingestion of port disruption feeds and IoT container telemetry.
2. **Assess:** Multi-factor scoring of shipment vulnerability based on cargo perishability, financial value, and SLA deadlines.
3. **Simulate:** Digital-twin modeling of alternate gateways, transit times, fuel overheads, and thermal exposure windows.
4. **Decide:** Multi-constraint AI optimization balancing delay, operational cost, and spoilage penalties.
5. **Protect:** Automated rerouting to viable gateways and immediate reassignment of nearby idle refrigerated trucks.

---

## Key Features

- **Multi-Constraint Optimization Engine:** Balances delay hours, fuel overhead, thermal exposure risk, and vehicle capacity penalties.
- **Live Cold-Chain Telemetry:** Continuous monitoring of biological cargo within the critical 2°C–8°C window with proactive excursion alarms.
- **Dynamic Idle Reefer Matching:** Queries available fleet databases to dispatch nearby refrigerated trucks directly to distressed shipments.
- **Explainable Decision Trace:** Generates transparent trade-off matrices showing dispatchers the exact rationale (hours saved, preserved cargo value vs. fuel delta).
- **Interactive Disruption Twin:** Enables dispatchers to stress-test scenarios (12 to 168 hours) to project network blast radius before execution.

---

## Tech Stack

- **Backend:** Python 3.10+, FastAPI, Uvicorn, Mangum (Serverless Handler)
- **Data & Interfaces:** Model Context Protocol (MCP) Connector, RESTful API
- **Frontend:** Reactive Command Deck (HTML5, CSS3, JavaScript)
- **Deployment:** Netlify Functions & GitHub Pages
- **Testing:** Pytest

---

## How to Run Locally

### Prerequisites
- Python 3.10+
- Git

### Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/dpuwar08/bob-ai-hackathon--Team-Chaos-.git](https://github.com/dpuwar08/bob-ai-hackathon--Team-Chaos-.git)
   cd bob-ai-hackathon--Team-Chaos-
