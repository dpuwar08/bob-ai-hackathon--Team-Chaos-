# Solution Overview: ChainGuard AI Autonomous Control Tower

## Executive Summary
**ChainGuard AI** is an intelligent, real-time logistics resilience engine designed to transform reactive supply chain monitoring into proactive, autonomous decision execution. Combining an asynchronous FastAPI computational engine with a high-fidelity glassmorphism dark-ops interface, ChainGuard AI detects maritime corridor disruptions instantly, models multi-tier ripple effects, and executes optimal rerouting strategies.

---

## Core Capabilities & Features

### 1. Autonomous Disruption Detection & Risk Scoring
- Real-time ingestion of maritime terminal disruption events (e.g., active strikes at Mumbai JNPT).
- Algorithmic composite risk scoring (scaled 0 to 100) combining corridor vulnerability, cargo sensitivity, and current dwell delays.

### 2. Multi-Objective Trade-Off Optimizer
When a disruption is triggered, the Pareto decision engine dynamically calculates three distinct mitigation options:
- **Express Route:** Minimizes operational latency and transit delays.
- **Eco Route:** Prioritizes fuel economics and lowest carbon ($CO_2$) emissions.
- **Budget Route:** Minimizes direct logistics surcharge and route diversion penalties.
- Intelligent selection logic automatically assigns the Express Route for life-critical temperature-sensitive vaccines while balancing standard dry cargo economically.

### 3. Cascading Blast-Radius Simulation
- Evaluates secondary downstream impacts beyond the immediate container:
  - Alternate hub congestion risk at secondary corridors (e.g., Mundra Port).
  - Cumulative idle truck hours across prime-mover fleets.
  - Projected financial SLA penalties with clear line-item breakdowns.

### 4. Cold-Chain IoT Telemetry & Thermal Alerts
- Live simulation and telemetry monitoring of refrigerated containers (reefers).
- Strict enforcement of the medical $2^\circ\text{C}$ to $8^\circ\text{C}$ thermal boundary with immediate breach notifications and idle reefer fleet reallocation.

### 5. What-If Disruption Sandbox
- Interactive dynamic simulation slider allowing operations engineers to test variable delay thresholds (1 to 48 hours) and evaluate real-time financial penalties before committing to physical freight diversion.

---

## Technical Stack
- **AI Development Partner:** IBM Bob Autonomous Developer Agent
- **Backend Framework:** FastAPI (Python 3.10+) with Uvicorn
- **Frontend Architecture:** Vanilla JavaScript, HTML5 Canvas, Tailwind CSS (Glassmorphism UI)
- **Geospatial & Visualization:** Leaflet.js (GIS dynamic route vectors), Chart.js (Thermal telemetry feeds)
- **Protocol Extensibility:** Model Context Protocol (MCP) server for live sensor data querying