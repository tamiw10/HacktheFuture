"""
Perception layer for supply chain disruption signals.

Ingests external disruption events (weather, border, supplier, shipping),
normalizes them into a common schema, correlates to affected shipments,
and updates operational data.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SIGNALS_FILE = DATA_DIR / "disruption_signals.json"


class SignalType(str, Enum):
    WEATHER_ALERT = "weather_alert"
    BORDER_CONGESTION = "border_congestion"
    SUPPLIER_NOTICE = "supplier_notice"
    SHIPPING_DELAY_UPDATE = "shipping_delay_update"


@dataclass
class DisruptionSignal:
    """Normalized disruption signal schema."""

    signal_id: str
    signal_type: SignalType
    severity: str  # low, medium, high, critical
    summary: str
    affected_regions: list[str] = field(default_factory=list)
    affected_supplier_ids: list[str] = field(default_factory=list)
    affected_shipment_ids: list[str] = field(default_factory=list)
    estimated_delay_days: int = 0
    raw_payload: dict[str, Any] = field(default_factory=dict)
    received_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "signal_type": self.signal_type.value,
            "severity": self.severity,
            "summary": self.summary,
            "affected_regions": self.affected_regions,
            "affected_supplier_ids": self.affected_supplier_ids,
            "affected_shipment_ids": self.affected_shipment_ids,
            "estimated_delay_days": self.estimated_delay_days,
            "received_at": self.received_at,
        }


def _load_signals() -> list[dict]:
    if not SIGNALS_FILE.exists():
        return []
    with open(SIGNALS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_signals(signals: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(SIGNALS_FILE, "w", encoding="utf-8") as f:
        json.dump(signals, f, indent=2)


def _load_json(filename: str) -> list[dict] | dict:
    with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_signal(raw: dict[str, Any]) -> DisruptionSignal:
    """
    Normalize an incoming raw disruption event into the common schema.
    """
    signal_type = SignalType(raw.get("signal_type", "shipping_delay_update"))
    signal_id = raw.get("signal_id") or f"SIG-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    return DisruptionSignal(
        signal_id=signal_id,
        signal_type=signal_type,
        severity=raw.get("severity", "medium"),
        summary=raw.get("summary", "Disruption detected"),
        affected_regions=raw.get("affected_regions", []),
        affected_supplier_ids=raw.get("affected_supplier_ids", []),
        affected_shipment_ids=raw.get("affected_shipment_ids", []),
        estimated_delay_days=int(raw.get("estimated_delay_days", 0)),
        raw_payload=raw,
        received_at=raw.get("received_at", datetime.now(timezone.utc).isoformat()),
    )


def correlate_to_shipments(signal: DisruptionSignal) -> list[str]:
    """
    Map a disruption signal to affected shipment IDs based on region, supplier, or explicit IDs.
    """
    shipments = _load_json("shipments.json")
    profiles = _load_json("manufacturer_profiles.json")
    manufacturer_to_region = {p["manufacturer_id"]: p["regional_exposure"]["primary_region"] for p in profiles}

    affected: set[str] = set()

    # Direct shipment IDs
    affected.update(signal.affected_shipment_ids)

    # By supplier
    if signal.affected_supplier_ids:
        for s in shipments:
            if s.get("supplier_id") in signal.affected_supplier_ids:
                affected.add(s["shipment_id"])

    # By region (manufacturer primary region)
    if signal.affected_regions:
        for s in shipments:
            region = manufacturer_to_region.get(s.get("manufacturer_id"), "")
            if region in signal.affected_regions:
                affected.add(s["shipment_id"])

    return list(affected)


def ingest_signal(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Ingest a raw disruption signal: normalize, correlate, persist, and optionally update shipments.
    """
    signal = normalize_signal(raw)
    correlated = correlate_to_shipments(signal)
    signal.affected_shipment_ids = list(set(signal.affected_shipment_ids) | set(correlated))

    # Persist
    signals = _load_signals()
    signals.append(signal.to_dict())
    _save_signals(signals)

    # Apply to shipments (update delay_days and status)
    if signal.estimated_delay_days > 0 and signal.affected_shipment_ids:
        _apply_disruption_to_shipments(signal)

    return {
        "signal_id": signal.signal_id,
        "signal_type": signal.signal_type.value,
        "correlated_shipments": signal.affected_shipment_ids,
        "status": "ingested",
    }


def _apply_disruption_to_shipments(signal: DisruptionSignal) -> None:
    """Update shipment delay_days and status based on the signal."""
    shipments = _load_json("shipments.json")
    for s in shipments:
        if s["shipment_id"] in signal.affected_shipment_ids:
            s["delay_days"] = s.get("delay_days", 0) + signal.estimated_delay_days
            s["status"] = "delayed"
            if "disruption_signals" not in s:
                s["disruption_signals"] = []
            s["disruption_signals"].append({
                "signal_id": signal.signal_id,
                "signal_type": signal.signal_type.value,
                "summary": signal.summary,
            })
    with open(DATA_DIR / "shipments.json", "w", encoding="utf-8") as f:
        json.dump(shipments, f, indent=2)


def get_signals_for_shipment(shipment_id: str) -> list[dict]:
    """Return all disruption signals that affected a given shipment."""
    signals = _load_signals()
    return [s for s in signals if shipment_id in s.get("affected_shipment_ids", [])]


def get_recent_signals(limit: int = 20) -> list[dict]:
    """Return the most recent disruption signals."""
    signals = _load_signals()
    return list(reversed(signals[-limit:]))
