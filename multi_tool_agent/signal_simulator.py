"""
Simulates incoming disruption signals for the perception layer.

Run: python -m multi_tool_agent.signal_simulator
"""

from datetime import datetime, timezone
import random
import time

from .perception import ingest_signal, SignalType

RNG = random.Random()


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def simulate_weather_alert() -> dict:
    delay = RNG.choice([1, 2])
    severity = "medium" if delay == 1 else "high"

    return ingest_signal({
        "signal_id": f"WX-{_ts()}",
        "signal_type": SignalType.WEATHER_ALERT.value,
        "severity": severity,
        "summary": f"Severe weather affecting cross-border logistics operations. Estimated delay: {delay} day(s).",
        "affected_regions": ["Mexico", "North America"],
        "estimated_delay_days": delay,
    })


def simulate_border_congestion() -> dict:
    delay = RNG.choice([1, 2])

    return ingest_signal({
        "signal_id": f"BRD-{_ts()}",
        "signal_type": SignalType.BORDER_CONGESTION.value,
        "severity": "medium",
        "summary": f"Border congestion causing customs processing delays. Estimated delay: {delay} day(s).",
        "affected_regions": ["Mexico", "North America"],
        "estimated_delay_days": delay,
    })


def simulate_supplier_notice() -> dict:
    delay = RNG.choice([1, 2])
    severity = "medium" if delay == 1 else "high"

    return ingest_signal({
        "signal_id": f"SUP-{_ts()}",
        "signal_type": SignalType.SUPPLIER_NOTICE.value,
        "severity": severity,
        "summary": f"SUP001 reports reduced output for Brake Control Module BCM-47. Estimated delay: {delay} day(s).",
        "affected_supplier_ids": ["SUP001"],
        "affected_regions": [],
        "estimated_delay_days": delay,
    })


def simulate_shipping_delay_update() -> dict:
    delay = RNG.choice([2, 3])
    severity = "medium" if delay == 2 else "high"

    return ingest_signal({
        "signal_id": f"SHIP-{_ts()}",
        "signal_type": SignalType.SHIPPING_DELAY_UPDATE.value,
        "severity": severity,
        "summary": f"Carrier reports route congestion affecting SHIP001 and SHIP002. Estimated delay: {delay} day(s).",
        "affected_shipment_ids": ["SHIP001", "SHIP002"],
        "estimated_delay_days": delay,
    })


def run_all_simulations(seed: int | None = None) -> list[dict]:
    """Run all signal simulations and return results."""
    if seed is None:
        seed = time.time_ns()  # changes every run
    RNG.seed(seed)

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