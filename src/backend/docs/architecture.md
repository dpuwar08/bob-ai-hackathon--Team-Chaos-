# System Architecture: ChainGuard AI Control Tower

## High-Level Architecture Overview
ChainGuard AI operates on a decoupled, asynchronous micro-architecture powered by an algorithmic decision backend and a reactive, event-driven telemetry dashboard.

```mermaid
flowchart TD
    subgraph UI ["User / Dashboard UI (Glassmorphism Control Tower)"]
        A1[GIS Corridor Map - Leaflet.js]
        A2[Thermal Telemetry Line Chart - Chart.js]
        A3[What-If Simulation Range Controller]
        A4[Cyber-Feed Real-Time Decision Logs]
    end

    subgraph Backend ["FastAPI Computation Engine"]
        B1["/api/shipments"]
        B2["/api/trigger-disruption"]
        B3["/api/optimize"]
        B4["/api/what-if"]
    end

    subgraph CoreEngine ["Algorithmic Decision Modules"]
        C1[Risk Scoring Engine 0-100]
        C2[Multi-Objective Trade-Off Matrix: Eco / Express / Budget]
        C3[Cascading Blast-Radius Calculator]
        C4[Cold-Chain Thermal Alert Monitor]
        C5[Idle Reefer Fleet Dispatcher]
    end

    subgraph Connectors ["Data & Context Protocols"]
        D1[Lightweight MCP Server - mcp_server.py]
        D2[Synthetic Logistics Datasets: Shipments, Fleet, Disruptions]
    end

    subgraph IBMBob ["IBM Bob Developer Agent Pipeline"]
        E1[Architecture Scaffolding & Data Modeling]
        E2[Deterministic Optimizer Logic & Test Synthesis]
        E3[Continuous Code Review /review & Quality Auditing]
    end

    UI <--> Backend
    Backend <--> CoreEngine
    CoreEngine <--> Connectors
    IBMBob -.-> CoreEngine
    IBMBob -.-> UI
    IBMBob -.-> Backend