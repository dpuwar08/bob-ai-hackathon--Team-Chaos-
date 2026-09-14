from __future__ import annotations

import pytest

from src.backend.optimizer import (
    calculate_blast_radius,
    calculate_risk_score,
    evaluate_alternate_routes,
    flag_cold_chain_alerts,
    generate_tradeoff_matrix,
)


@pytest.fixture
def critical_vaccine() -> dict:
    return {
        "id": "SHP-TEST-001",
        "reference": "Critical vaccine load",
        "priority": "critical",
        "status": "in_transit",
        "disruptionRisk": "high",
        "weightKg": 100,
        "temperature": {
            "requiredMinCelsius": 2,
            "requiredMaxCelsius": 8,
            "currentCelsius": 5,
        },
    }


@pytest.fixture
def mumbai_strike() -> dict:
    return {
        "id": "DIS-TEST-001",
        "name": "Mumbai Port Strike",
        "status": "active",
        "impact": {
            "severity": "high",
            "estimatedDelayHours": {"min": 12, "max": 48},
            "affectedShipmentIds": ["SHP-TEST-001", "SHP-OTHER-001"],
        },
    }


def test_risk_score_combines_priority_status_disruption_and_stays_bounded(
    critical_vaccine: dict, mumbai_strike: dict
) -> None:
    # 10 base + 24 critical + 5 in-transit + 22 high risk + 28 active high disruption.
    assert calculate_risk_score(critical_vaccine, [mumbai_strike]) == 89
    assert 0 <= calculate_risk_score(critical_vaccine, [mumbai_strike]) <= 100


def test_risk_score_clamps_extreme_temperature_and_disruption() -> None:
    shipment = {
        "id": "SHP-TEST-HOT",
        "priority": "critical",
        "status": "delayed",
        "disruptionRisk": "high",
        "temperature": {"requiredMaxCelsius": 8, "currentCelsius": 15},
    }
    disruption = {
        "status": "active",
        "impact": {"severity": "high", "affectedShipmentIds": ["SHP-TEST-HOT"]},
    }
    assert calculate_risk_score(shipment, [disruption]) == 100


def test_cold_chain_alert_does_not_trigger_at_exact_threshold() -> None:
    shipment = {
        "id": "SHP-AT-LIMIT",
        "reference": "Temperature limit sample",
        "temperature": {"requiredMaxCelsius": 8, "currentCelsius": 8},
    }
    assert flag_cold_chain_alerts([shipment]) == []


def test_cold_chain_alert_triggers_above_eight_degrees() -> None:
    shipment = {
        "id": "SHP-ABOVE-LIMIT",
        "reference": "Over-temperature sample",
        "temperature": {"requiredMaxCelsius": 8, "currentCelsius": 8.1},
    }
    alerts = flag_cold_chain_alerts([shipment])
    assert len(alerts) == 1
    assert alerts[0]["shipmentId"] == "SHP-ABOVE-LIMIT"
    assert alerts[0]["severity"] == "high"


def test_alternate_route_cost_equation_is_preserved(critical_vaccine: dict) -> None:
    routes = evaluate_alternate_routes(critical_vaccine, [])
    mumbai = next(route for route in routes if route["name"] == "Mumbai")
    expected = round(4 * 1.2 + (18500 / 400) * 0.25 + 30 * 0.8)
    assert mumbai["delayHours"] == 4
    assert mumbai["costInr"] == 18500
    assert mumbai["evaluationScore"] == expected
    assert mumbai["coldChainCompatible"] is True


def test_disrupted_alternate_route_uses_mumbai_and_mundra_costs(
    critical_vaccine: dict, mumbai_strike: dict
) -> None:
    routes = evaluate_alternate_routes(critical_vaccine, [mumbai_strike])
    by_name = {route["name"]: route for route in routes}
    assert by_name["Mumbai"]["delayHours"] == 36
    assert by_name["Mumbai"]["costInr"] == 18500
    assert by_name["Mundra"]["delayHours"] == 18
    assert by_name["Mundra"]["costInr"] == 27800
    assert any(route["recommendation"] == "recommended" for route in routes)


def test_blast_radius_projects_congestion_idle_hours_and_penalty(
    critical_vaccine: dict, mumbai_strike: dict
) -> None:
    fleet = [{"id": "TRK-IDLE-1", "status": "idle"}, {"id": "TRK-ACTIVE", "status": "active"}]
    blast = calculate_blast_radius(critical_vaccine, mumbai_strike, fleet)
    # Average delay 30h; congestion = 25 + 30*1.4 + 2*8 + 18 = 109, clamped to 100.
    assert blast["warehouseCongestion"]["riskScore"] == 100
    assert blast["downstreamTruckImpact"]["estimatedIdleHours"] == 36.0
    assert blast["downstreamTruckImpact"]["idleTruckIds"] == ["TRK-IDLE-1"]
    assert blast["financialPenalty"]["components"] == {
        "delayExposure": 51300,
        "warehouseHandling": 240,
        "congestionOverhead": 11500,
    }
    assert blast["financialPenalty"]["projectedAmount"] == 63040


def test_tradeoff_matrix_returns_three_objectives_and_priority_rationale(
    critical_vaccine: dict, mumbai_strike: dict
) -> None:
    matrix = generate_tradeoff_matrix(critical_vaccine, [mumbai_strike])
    assert {route["name"] for route in matrix["routes"]} == {
        "Eco Route",
        "Express Route",
        "Budget Route",
    }
    assert matrix["cargoPriority"] == "critical"
    assert matrix["weights"]["delay"] > matrix["weights"]["cost"]
    highest_score = max(route["score"] for route in matrix["routes"])
    assert matrix["recommendedRoute"] == next(
        route["name"] for route in matrix["routes"] if route["score"] == highest_score
    )
    assert matrix["recommendedRoute"] == "Eco Route"
    assert "critical-priority cargo" in matrix["selectionRationale"]
    assert all(0 <= route["score"] <= 100 for route in matrix["routes"])
