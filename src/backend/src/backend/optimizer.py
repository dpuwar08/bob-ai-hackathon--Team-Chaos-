from __future__ import annotations

from typing import Any, Mapping, Sequence


def _clamp(value: float, minimum: float = 0, maximum: float = 100) -> int:
    return round(max(minimum, min(maximum, value)))


def calculate_risk_score(
    shipment: Mapping[str, Any], disruptions: Sequence[Mapping[str, Any]] = ()
) -> int:
    score = 10
    score += {"standard": 0, "high": 12, "critical": 24}.get(shipment.get("priority"), 5)
    score += {"scheduled": 0, "in_transit": 5, "delayed": 20}.get(shipment.get("status"), 8)
    score += {"low": 0, "medium": 10, "high": 22}.get(shipment.get("disruptionRisk"), 5)

    temperature = shipment.get("temperature") or {}
    current_temperature = temperature.get("currentCelsius")
    maximum_temperature = temperature.get("requiredMaxCelsius", 8)
    if current_temperature is not None:
        if current_temperature > maximum_temperature:
            score += 35
        elif current_temperature > 7:
            score += 12

    shipment_id = shipment.get("id")
    for disruption in disruptions:
        impact = disruption.get("impact") or {}
        if disruption.get("status") == "active" and shipment_id in impact.get("affectedShipmentIds", []):
            score += {"low": 8, "medium": 15, "high": 28}.get(impact.get("severity"), 15)

    return _clamp(score)


def evaluate_alternate_routes(
    shipment: Mapping[str, Any], disruptions: Sequence[Mapping[str, Any]] = ()
) -> list[dict[str, Any]]:
    affected_by_port_strike = any(
        disruption.get("status") == "active"
        and disruption.get("name") == "Mumbai Port Strike"
        and shipment.get("id") in (disruption.get("impact") or {}).get("affectedShipmentIds", [])
        for disruption in disruptions
    )
    cold_chain = shipment.get("temperature") is not None
    route_profiles = [
        {"name": "Mumbai", "delayHours": 36 if affected_by_port_strike else 4, "costInr": 18500, "risk": 82 if affected_by_port_strike else 30},
        {"name": "Mundra", "delayHours": 18 if affected_by_port_strike else 16, "costInr": 27800, "risk": 45 if affected_by_port_strike else 38},
    ]
    for route in route_profiles:
        normalized_cost = route["costInr"] / 400
        route["coldChainCompatible"] = cold_chain
        route["evaluationScore"] = _clamp(
            route["delayHours"] * 1.2 + normalized_cost * 0.25 + route["risk"] * 0.8
        )
        route["recommendation"] = "preferred" if route["name"] == "Mundra" and affected_by_port_strike else "alternative"
    route_profiles.sort(key=lambda route: route["evaluationScore"])
    route_profiles[0]["recommendation"] = "recommended"
    return route_profiles


def calculate_blast_radius(
    shipment: Mapping[str, Any],
    disruption: Mapping[str, Any],
    fleet: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Project operational and financial secondary impacts of a disruption."""

    impact = disruption.get("impact") or {}
    delay_range = impact.get("estimatedDelayHours") or {}
    if isinstance(delay_range, Mapping):
        delay_hours = (delay_range.get("min", 0) + delay_range.get("max", 0)) / 2
    else:
        delay_hours = float(delay_range or 0)

    priority = shipment.get("priority", "standard")
    priority_factor = {"standard": 1.0, "high": 1.35, "critical": 1.8}.get(priority, 1.0)
    cargo_weight = float(shipment.get("weightKg", 0))
    affected_ids = set(impact.get("affectedShipmentIds", []))
    affected_count = max(1, len(affected_ids))
    congestion_risk = _clamp(25 + delay_hours * 1.4 + affected_count * 8 + (18 if priority == "critical" else 0))

    alternative_hub = "Mundra Gateway" if "Mumbai" in str(disruption.get("name", "")) else "Nearest regional staging hub"
    idle_hours = round(delay_hours * (1.0 + min(0.5, affected_count * 0.1)), 1)
    available_trucks = sum(1 for truck in fleet if truck.get("status") == "idle")
    idle_truck_ids = [truck.get("id") for truck in fleet if truck.get("status") == "idle"]
    handling_penalty = cargo_weight * 2.4
    delay_penalty = delay_hours * 950 * priority_factor
    congestion_penalty = congestion_risk * 115
    financial_penalty = round(delay_penalty + handling_penalty + congestion_penalty)

    return {
        "disruptionId": disruption.get("id"),
        "disruptionName": disruption.get("name"),
        "primaryShipmentId": shipment.get("id"),
        "alternativeHub": alternative_hub,
        "warehouseCongestion": {
            "riskScore": congestion_risk,
            "level": "critical" if congestion_risk >= 75 else "high" if congestion_risk >= 50 else "moderate",
            "reason": f"{affected_count} shipment(s) share the disrupted lane with an average {delay_hours:g} hour delay.",
        },
        "downstreamTruckImpact": {
            "estimatedIdleHours": idle_hours,
            "idleTruckCount": available_trucks,
            "idleTruckIds": idle_truck_ids,
            "risk": "high" if idle_hours >= 24 else "moderate" if idle_hours >= 8 else "low",
        },
        "financialPenalty": {
            "currency": "INR",
            "projectedAmount": financial_penalty,
            "components": {
                "delayExposure": round(delay_penalty),
                "warehouseHandling": round(handling_penalty),
                "congestionOverhead": round(congestion_penalty),
            },
        },
    }


def generate_tradeoff_matrix(
    shipment: Mapping[str, Any], disruptions: Sequence[Mapping[str, Any]] = ()
) -> dict[str, Any]:
    """Score Eco, Express, and Budget route objectives for a shipment."""

    disrupted = any(
        item.get("status") == "active"
        and shipment.get("id") in (item.get("impact") or {}).get("affectedShipmentIds", [])
        for item in disruptions
    )
    priority = shipment.get("priority", "standard")
    weights = {
        "critical": {"delay": 0.55, "risk": 0.3, "cost": 0.1, "emissions": 0.05},
        "high": {"delay": 0.4, "risk": 0.3, "cost": 0.2, "emissions": 0.1},
        "standard": {"delay": 0.2, "risk": 0.2, "cost": 0.4, "emissions": 0.2},
    }.get(priority, {"delay": 0.25, "risk": 0.25, "cost": 0.3, "emissions": 0.2})
    routes = [
        {"name": "Eco Route", "gateway": "Mundra", "delayHours": 26 if disrupted else 22, "costInr": 25200, "co2Kg": 410, "risk": 34},
        {"name": "Express Route", "gateway": "Navi Mumbai", "delayHours": 8 if not disrupted else 20, "costInr": 32100, "co2Kg": 690, "risk": 48 if disrupted else 25},
        {"name": "Budget Route", "gateway": "Mumbai", "delayHours": 16 if not disrupted else 42, "costInr": 16400, "co2Kg": 820, "risk": 78 if disrupted else 42},
    ]
    max_values = {key: max(route[key] for route in routes) for key in ("delayHours", "costInr", "co2Kg", "risk")}
    for route in routes:
        normalized = {
            "delay": route["delayHours"] / max_values["delayHours"],
            "cost": route["costInr"] / max_values["costInr"],
            "emissions": route["co2Kg"] / max_values["co2Kg"],
            "risk": route["risk"] / max_values["risk"],
        }
        route["score"] = _clamp(100 * (1 - sum(weights[key] * normalized[key] for key in weights)))
        route["rationale"] = (
            f"{route['name']} prioritizes "
            + {"Eco Route": "lower CO2 emissions", "Express Route": "minimum delay", "Budget Route": "lowest transport cost"}[route["name"]]
            + f" ({route['delayHours']}h / INR {route['costInr']:,} / {route['co2Kg']}kg CO2)."
        )
    routes.sort(key=lambda route: route["score"], reverse=True)
    chosen = routes[0]
    return {
        "cargoPriority": priority,
        "weights": weights,
        "disrupted": disrupted,
        "routes": routes,
        "recommendedRoute": chosen["name"],
        "selectionRationale": (
            f"AI selects {chosen['name']} for {priority}-priority cargo because its weighted score of "
            f"{chosen['score']}/100 best balances delay, risk, cost, and emissions."
        ),
    }


def flag_cold_chain_alerts(shipments: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    for shipment in shipments:
        temperature = shipment.get("temperature") or {}
        current_temperature = temperature.get("currentCelsius")
        maximum_temperature = temperature.get("requiredMaxCelsius", 8)
        if current_temperature is not None and current_temperature > maximum_temperature:
            alerts.append(
                {
                    "shipmentId": shipment.get("id"),
                    "reference": shipment.get("reference"),
                    "currentCelsius": current_temperature,
                    "maximumAllowedCelsius": maximum_temperature,
                    "severity": "critical" if current_temperature > 10 else "high",
                    "message": "Cold-chain temperature is above the permitted range.",
                }
            )
    return alerts


def match_idle_trucks(
    shipment: Mapping[str, Any], fleet: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    required_weight = shipment.get("weightKg", 0)
    requires_refrigeration = shipment.get("temperature") is not None
    matches = []
    for truck in fleet:
        refrigeration = truck.get("refrigeration") or {}
        if truck.get("status") != "idle" or truck.get("capacityKg", 0) < required_weight:
            continue
        if requires_refrigeration and not refrigeration.get("available"):
            continue
        matches.append(
            {
                "truckId": truck.get("id"),
                "registration": truck.get("registration"),
                "driver": truck.get("driver"),
                "location": truck.get("currentLocation"),
                "capacityKg": truck.get("capacityKg"),
                "refrigerated": refrigeration.get("available", False),
                "capacityBufferKg": truck.get("capacityKg", 0) - required_weight,
            }
        )
    return sorted(matches, key=lambda truck: truck["capacityBufferKg"])