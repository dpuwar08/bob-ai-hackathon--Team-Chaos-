"""Lightweight MCP connector for BOB's disruption and telemetry tools.

The module has no third-party MCP dependency. It exposes the standard MCP
JSON-RPC methods over stdin/stdout and also provides a Python connector for
the FastAPI decision engine.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping


DATA_DIR = Path(__file__).parent / "data"

TOOL_DEFINITIONS = [
    {
        "name": "get_active_disruptions",
        "description": "Return active logistics disruptions affecting a port or city.",
        "inputSchema": {
            "type": "object",
            "properties": {"port_name": {"type": "string", "description": "Port or city to inspect."}},
            "required": ["port_name"],
        },
    },
    {
        "name": "get_telemetry_stream",
        "description": "Return the latest cold-chain temperature telemetry for a shipment.",
        "inputSchema": {
            "type": "object",
            "properties": {"shipment_id": {"type": "string", "description": "Shipment identifier."}},
            "required": ["shipment_id"],
        },
    },
]


def _load_json(filename: str) -> dict[str, Any]:
    with (DATA_DIR / filename).open(encoding="utf-8") as data_file:
        return json.load(data_file)


class BOBMCPConnector:
    """Read-only connector used by both MCP clients and the decision engine."""

    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self.data_dir = data_dir

    def _load(self, filename: str) -> dict[str, Any]:
        with (self.data_dir / filename).open(encoding="utf-8") as data_file:
            return json.load(data_file)

    def get_active_disruptions(self, port_name: str) -> dict[str, Any]:
        query = port_name.strip().lower()
        disruptions = []
        for disruption in self._load("disruptions.json").get("disruptions", []):
            location = disruption.get("location") or {}
            facilities = location.get("facilities") or []
            searchable = [disruption.get("name", ""), location.get("city", ""), *facilities]
            if disruption.get("status") == "active" and any(query in str(value).lower() for value in searchable):
                disruptions.append(disruption)
        return {"portName": port_name, "count": len(disruptions), "disruptions": disruptions}

    def get_telemetry_stream(self, shipment_id: str) -> dict[str, Any]:
        shipments = self._load("shipments.json").get("shipments", [])
        shipment = next((item for item in shipments if item.get("id") == shipment_id), None)
        if shipment is None:
            return {"shipmentId": shipment_id, "found": False, "readings": []}

        temperature = shipment.get("temperature") or {}
        current = temperature.get("currentCelsius")
        if current is None:
            return {
                "shipmentId": shipment_id,
                "found": True,
                "coldChain": False,
                "unit": "celsius",
                "readings": [],
                "message": "Shipment does not require temperature monitoring.",
            }

        base_time = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        offsets = (-25, -20, -15, -10, -5, 0)
        readings = [
            {
                "recordedAt": (base_time + timedelta(minutes=offset)).isoformat(),
                "celsius": round(float(current) + (index % 3 - 1) * 0.2, 1),
            }
            for index, offset in enumerate(offsets)
        ]
        return {
            "shipmentId": shipment_id,
            "found": True,
            "coldChain": True,
            "unit": "celsius",
            "requiredRange": {
                "min": temperature.get("requiredMinCelsius", 2),
                "max": temperature.get("requiredMaxCelsius", 8),
            },
            "latest": readings[-1],
            "readings": readings,
        }


def call_tool(name: str, arguments: Mapping[str, Any], connector: BOBMCPConnector | None = None) -> dict[str, Any]:
    connector = connector or BOBMCPConnector()
    if name == "get_active_disruptions":
        return connector.get_active_disruptions(str(arguments.get("port_name", "")))
    if name == "get_telemetry_stream":
        return connector.get_telemetry_stream(str(arguments.get("shipment_id", "")))
    raise ValueError(f"Unknown MCP tool: {name}")


def handle_message(message: Mapping[str, Any], connector: BOBMCPConnector | None = None) -> dict[str, Any] | None:
    """Handle one MCP JSON-RPC request. Notifications intentionally return no response."""

    method = message.get("method")
    request_id = message.get("id")
    if request_id is None and method not in {"initialize", "tools/list", "tools/call"}:
        return None
    try:
        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "bob-logistics-mcp", "version": "1.0.0"},
            }
        elif method == "notifications/initialized":
            return None
        elif method == "tools/list":
            result = {"tools": TOOL_DEFINITIONS}
        elif method == "tools/call":
            params = message.get("params") or {}
            value = call_tool(str(params.get("name", "")), params.get("arguments") or {}, connector)
            result = {"content": [{"type": "text", "text": json.dumps(value)}], "structuredContent": value}
        else:
            raise ValueError(f"Unsupported MCP method: {method}")
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    except (OSError, TypeError, ValueError, KeyError) as error:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": str(error)}}


def main() -> None:
    """Run the MCP JSON-RPC transport over newline-delimited stdin/stdout."""

    connector = BOBMCPConnector()
    for line in sys.stdin:
        if not line.strip():
            continue
        response = handle_message(json.loads(line), connector)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()