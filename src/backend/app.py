from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
  from mangum import Mangum
except ImportError:
  Mangum = None

try:
  from .mcp_server import BOBMCPConnector
except ImportError:
  from mcp_server import BOBMCPConnector

try:
  from .optimizer import (
      calculate_blast_radius,
      calculate_risk_score,
      evaluate_alternate_routes,
      flag_cold_chain_alerts,
      generate_tradeoff_matrix,
      match_idle_trucks,
  )
except ImportError:
  from optimizer import (
      calculate_blast_radius,
      calculate_risk_score,
      evaluate_alternate_routes,
      flag_cold_chain_alerts,
      generate_tradeoff_matrix,
      match_idle_trucks,
  )


DATA_DIR = Path(__file__).parent / "data"
MCP_CONNECTOR = BOBMCPConnector(DATA_DIR)

app = FastAPI(title="BOB Logistics Optimizer", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DisruptionRequest(BaseModel):
  disruptionId: str | None = None
  name: str = "Mumbai Port Strike"
  status: str = "active"
  severity: str = "high"
  delayHours: int = Field(default=24, ge=0, le=168)
  affectedShipmentIds: list[str] = Field(default_factory=list)


class OptimizeRequest(BaseModel):
  shipmentId: str | None = None


class WhatIfRequest(BaseModel):
  shipmentId: str | None = None
  disruptionId: str | None = None
  disruptionName: str = "Mumbai Port Strike"
  delayHours: int = Field(default=24, ge=0, le=168)
  severity: str = "high"


def load_json(filename: str) -> dict[str, Any]:
  with (DATA_DIR / filename).open(encoding="utf-8") as data_file:
    return json.load(data_file)


def load_data(
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
  shipments = load_json("shipments.json")["shipments"]
  fleet = load_json("fleet.json")["fleet"]
  disruptions = load_json("disruptions.json")["disruptions"]
  return shipments, fleet, disruptions


def get_decision_disruptions(
    disruptions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
  """Refresh active Mumbai signals through MCP before scoring decisions."""
  live_mumbai = MCP_CONNECTOR.get_active_disruptions("Mumbai")["disruptions"]
  live_ids = {item.get("id") for item in live_mumbai}
  retained = [item for item in disruptions if item.get("id") not in live_ids]
  return retained + live_mumbai


def find_shipment(
    shipment_id: str, shipments: list[dict[str, Any]]
) -> dict[str, Any]:
  shipment = next(
      (item for item in shipments if item.get("id") == shipment_id), None
  )
  if shipment is None:
    raise HTTPException(
        status_code=404, detail=f"Shipment {shipment_id} was not found"
    )
  return shipment


@app.get("/")
def root() -> dict[str, str]:
  return {
      "message": "BOB Logistics Optimizer API is active",
      "docs": "/docs",
  }


@app.get("/api/shipments")
def get_shipments() -> dict[str, Any]:
  shipments, fleet, disruptions = load_data()
  decision_disruptions = get_decision_disruptions(disruptions)
  cold_chain_alerts = flag_cold_chain_alerts(shipments)
  active_disruptions = MCP_CONNECTOR.get_active_disruptions("Mumbai")
  enriched_shipments = []
  for shipment in shipments:
    enriched = deepcopy(shipment)
    enriched["riskScore"] = calculate_risk_score(shipment, decision_disruptions)
    enriched["coldChainAlerts"] = [
        alert
        for alert in cold_chain_alerts
        if alert["shipmentId"] == shipment.get("id")
    ]
    enriched["assignedTruck"] = next(
        (
            truck
            for truck in fleet
            if truck.get("id") == shipment.get("assignedTruckId")
        ),
        None,
    )
    enriched_shipments.append(enriched)
  return {
      "shipments": enriched_shipments,
      "coldChainAlerts": cold_chain_alerts,
      "fleet": fleet,
      "mcpSignals": {"activeDisruptions": active_disruptions},
  }


@app.post("/api/trigger-disruption")
def trigger_disruption(request: DisruptionRequest) -> dict[str, Any]:
  shipments, _, disruptions = load_data()
  disruption = next(
      (
          item
          for item in disruptions
          if request.disruptionId and item.get("id") == request.disruptionId
      ),
      None,
  )
  if disruption is None:
    affected_ids = request.affectedShipmentIds or [
        shipment["id"]
        for shipment in shipments
        if shipment.get("destination", "").endswith("Mumbai")
    ]
    disruption = {
        "id": request.disruptionId or "SIMULATED-DISRUPTION",
        "name": request.name,
        "status": request.status,
        "severity": request.severity,
        "impact": {
            "estimatedDelayHours": request.delayHours,
            "affectedShipmentIds": affected_ids,
        },
    }
  else:
    disruption = deepcopy(disruption)
    disruption["status"] = request.status
  for shipment in shipments:
    if shipment.get("id") in (disruption.get("impact") or {}).get(
        "affectedShipmentIds", []
    ):
      shipment["status"] = "delayed"
      shipment["disruptionRisk"] = "high"
  return {"disruption": disruption, "affectedShipments": shipments}


@app.post("/api/optimize")
def optimize(request: OptimizeRequest) -> dict[str, Any]:
  shipments, fleet, disruptions = load_data()
  decision_disruptions = get_decision_disruptions(disruptions)
  shipment = (
      find_shipment(request.shipmentId, shipments)
      if request.shipmentId
      else shipments[0]
  )
  telemetry = MCP_CONNECTOR.get_telemetry_stream(shipment["id"])
  active_disruptions = MCP_CONNECTOR.get_active_disruptions("Mumbai")
  active_disruption = next(
      (item for item in decision_disruptions if item.get("status") == "active"),
      {"name": "No active disruption", "impact": {}},
  )
  return {
      "shipment": shipment,
      "riskScore": calculate_risk_score(shipment, decision_disruptions),
      "routes": evaluate_alternate_routes(shipment, decision_disruptions),
      "idleTruckMatches": match_idle_trucks(shipment, fleet),
      "coldChainAlerts": flag_cold_chain_alerts([shipment]),
      "mcpSignals": {
          "activeDisruptions": active_disruptions,
          "telemetry": telemetry,
      },
      "blastRadius": calculate_blast_radius(
          shipment, active_disruption, fleet
      ),
      "tradeoffMatrix": generate_tradeoff_matrix(
          shipment, decision_disruptions
      ),
  }


@app.post("/api/what-if")
def what_if(request: WhatIfRequest) -> dict[str, Any]:
  shipments, fleet, disruptions = load_data()
  decision_disruptions = get_decision_disruptions(disruptions)
  simulated_shipments = deepcopy(shipments)
  shipment = (
      find_shipment(request.shipmentId, simulated_shipments)
      if request.shipmentId
      else simulated_shipments[0]
  )
  simulated_disruption = {
      "id": request.disruptionId or "WHAT-IF-DISRUPTION",
      "name": request.disruptionName,
      "status": "active",
      "impact": {
          "severity": request.severity,
          "estimatedDelayHours": request.delayHours,
          "affectedShipmentIds": [shipment["id"]],
      },
  }
  simulated_disruptions = decision_disruptions + [simulated_disruption]
  telemetry = MCP_CONNECTOR.get_telemetry_stream(shipment["id"])
  return {
      "scenario": simulated_disruption,
      "shipment": shipment,
      "riskScore": calculate_risk_score(shipment, simulated_disruptions),
      "routes": evaluate_alternate_routes(shipment, simulated_disruptions),
      "idleTruckMatches": match_idle_trucks(shipment, fleet),
      "mcpSignals": {"telemetry": telemetry},
      "blastRadius": calculate_blast_radius(
          shipment, simulated_disruption, fleet
      ),
      "tradeoffMatrix": generate_tradeoff_matrix(
          shipment, simulated_disruptions
      ),
  }


# Serverless adapter entry point for Netlify/AWS Lambda
handler = Mangum(app) if Mangum else app