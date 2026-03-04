"""
Simulates incoming disruption signals for the perception layer.

Run: python -m multi_tool_agent.signal_simulator
"""

from datetime import datetime, timezone

from .perception import ingest_signal, SignalType


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def simulate_weather_alert() -> dict:
    return ingest_signal({
        "signal_id": f"WX-{_ts()}",
        "signal_type": SignalType.WEATHER_ALERT.value,
        "severity": "medium",
        "summary": "Severe weather affecting cross-border logistics operations.",
        "affected_regions": ["Mexico", "North America"],
        "estimated_delay_days": 2,
    })


def simulate_border_congestion() -> dict:
    return ingest_signal({
        "signal_id": f"BRD-{_ts()}",
        "signal_type": SignalType.BORDER_CONGESTION.value,
        "severity": "medium",
        "summary": "Border congestion causing customs processing delays.",
        "affected_regions": ["Mexico", "North America"],
        "estimated_delay_days": 1,
    })


def simulate_supplier_notice() -> dict:
    return ingest_signal({
        "signal_id": f"SUP-{_ts()}",
        "signal_type": SignalType.SUPPLIER_NOTICE.value,
        "severity": "high",
        "summary": "SUP001 reports reduced output for Brake Control Module BCM-47.",
        "affected_supplier_ids": ["SUP001"],
        "affected_regions": [],
        "estimated_delay_days": 1,
    })


def simulate_shipping_delay_update() -> dict:
    return ingest_signal({
        "signal_id": f"SHIP-{_ts()}",
        "signal_type": SignalType.SHIPPING_DELAY_UPDATE.value,
        "severity": "medium",
        "summary": "Carrier reports route congestion affecting SHIP001 and SHIP002.",
        "affected_shipment_ids": ["SHIP001", "SHIP002"],
        "estimated_delay_days": 2,
    })


def run_all_simulations() -> list[dict]:
    """Run all signal simulations and return results."""
    results = []
    for name, fn in [
        ("weather_alert", simulate_weather_alert),
        ("border_congestion", simulate_border_congestion),
        ("supplier_notice", simulate_supplier_notice),
        ("shipping_delay_update", simulate_shipping_delay_update),
    ]:
        result = fn()
        results.append({"signal_type": name, "result": result})
    return results


if __name__ == "__main__":
    print("Simulating incoming disruption signals...\n")
    for item in run_all_simulations():
        print(f"[{item['signal_type']}]")
        print(f"  {item['result']}\n")
    print("Done. Check data/disruption_signals.json and data/shipments.json.")
