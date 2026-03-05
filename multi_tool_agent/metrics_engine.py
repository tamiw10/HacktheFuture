from __future__ import annotations

from typing import Any, Dict


def _get_inventory_days(case_summary: dict) -> int:
    return int(case_summary["inventory"]["days_remaining"])


def _get_delay_days(case_summary: dict) -> int:
    return int(case_summary["shipment"]["delay_days"])


def _get_daily_usage_units(case_summary: dict) -> int:
    return int(case_summary["part"].get("daily_usage_units", 0))


def _get_expedite_option(case_summary: dict) -> dict | None:
    for option in case_summary.get("mitigation_options", []):
        if option.get("option_type") == "expedite_shipment" and option.get("available"):
            return option
    return None


def _compute_gap_from_delay(delay_days: int, inventory_days: int) -> int:
    return max(0, delay_days - inventory_days)


def compute_stockout_gap_days(case_summary: dict, use_mitigation: bool = False) -> int:
    """
    Return stockout gap days.
    If use_mitigation=True, apply expedite time savings when available.
    """
    delay_days = _get_delay_days(case_summary)
    inventory_days = _get_inventory_days(case_summary)

    if use_mitigation:
        expedite_option = _get_expedite_option(case_summary)
        if expedite_option:
            time_saved = int(expedite_option.get("estimated_time_saved_days", 0))
            delay_days = max(0, delay_days - time_saved)

    return _compute_gap_from_delay(delay_days, inventory_days)


def estimate_revenue_at_risk_cad(case_summary: dict, params: dict, use_mitigation: bool = False) -> float:
    stockout_gap_days = compute_stockout_gap_days(case_summary, use_mitigation=use_mitigation)
    daily_usage_units = _get_daily_usage_units(case_summary)
    selling_price_per_unit_cad = float(params["selling_price_per_unit_cad"])
    return stockout_gap_days * daily_usage_units * selling_price_per_unit_cad


def estimate_margin_at_risk_cad(case_summary: dict, params: dict, use_mitigation: bool = False) -> float:
    stockout_gap_days = compute_stockout_gap_days(case_summary, use_mitigation=use_mitigation)
    daily_usage_units = _get_daily_usage_units(case_summary)
    contribution_margin_per_unit_cad = float(params["contribution_margin_per_unit_cad"])
    return stockout_gap_days * daily_usage_units * contribution_margin_per_unit_cad


def estimate_service_level_impact(case_summary: dict, params: dict, use_mitigation: bool = False) -> dict:
    """
    Returns service-level impact as late units and % point drop.
    """
    stockout_gap_days = compute_stockout_gap_days(case_summary, use_mitigation=use_mitigation)
    daily_usage_units = _get_daily_usage_units(case_summary)
    committed_units_in_window = max(1, int(params["committed_units_in_window"]))

    late_units = stockout_gap_days * daily_usage_units
    service_level_drop_pct = (late_units / committed_units_in_window) * 100.0
    protected_service_level_pct = max(0.0, 100.0 - service_level_drop_pct)

    return {
        "late_units": late_units,
        "service_level_drop_pct_points": service_level_drop_pct,
        "protected_service_level_pct": protected_service_level_pct,
    }


def estimate_expedite_cost_cad(case_summary: dict, params: dict) -> dict:
    shipment = case_summary["shipment"]
    base_transport_cost_cad = float(
        shipment.get("base_transport_cost_cad", params.get("base_transport_cost_cad_default", 12000))
    )

    delay_days = int(shipment.get("delay_days", 0))

    base_mult = float(params.get("expedite_multiplier_base", 1.10))
    per_day = float(params.get("expedite_multiplier_per_delay_day", 0.02))

    # Multiplier grows with disruption severity (delay)
    multiplier = base_mult + per_day * delay_days

    # clamp to avoid absurd quotes in demos
    multiplier = max(1.05, min(multiplier, 1.60))

    expedite_quote_cad = base_transport_cost_cad * multiplier
    premium_cad = max(0.0, expedite_quote_cad - base_transport_cost_cad)
    premium_pct = ((premium_cad / base_transport_cost_cad) * 100.0) if base_transport_cost_cad else 0.0

    return {
        "base_transport_cost_cad": round(base_transport_cost_cad, 2),
        "expedite_quote_cad": round(expedite_quote_cad, 2),
        "expedite_premium_cad": round(premium_cad, 2),
        "expedite_premium_pct": round(premium_pct, 2),
        "multiplier_used": round(multiplier, 3),
    }


def estimate_sla_penalty_cad(case_summary: dict, params: dict, use_mitigation: bool = False) -> float:
    service = estimate_service_level_impact(case_summary, params, use_mitigation=use_mitigation)
    late_units = service["late_units"]
    sla_penalty_per_unit_cad = float(params["sla_penalty_per_unit_cad"])
    return late_units * sla_penalty_per_unit_cad


def estimate_downtime_cost_cad(case_summary: dict, params: dict, use_mitigation: bool = False) -> float:
    stockout_gap_days = compute_stockout_gap_days(case_summary, use_mitigation=use_mitigation)
    line_downtime_cost_per_day_cad = float(params["line_downtime_cost_per_day_cad"])
    return stockout_gap_days * line_downtime_cost_per_day_cad


def estimate_inventory_adjustment_cost_cad(case_summary: dict, reorder_suggestion: dict, params: dict) -> float:
    suggested_extra_units = int(reorder_suggestion.get("suggested_extra_units", 0))
    unit_cost_cad = float(params["unit_cost_cad"])
    carrying_cost_factor_for_window = float(params.get("carrying_cost_factor_for_window", 0.02))
    return suggested_extra_units * unit_cost_cad * carrying_cost_factor_for_window


def compare_scenarios_with_without_agent(case_summary: dict, params: dict) -> dict:
    """
    Compare:
    - without agent: manual response lag, no immediate mitigation
    - with agent: immediate risk assessment + expedite if available

    Returns the four business outcomes in CAD/percentage/day terms.
    """
    shipment = case_summary["shipment"]
    inventory_days = _get_inventory_days(case_summary)
    original_delay_days = _get_delay_days(case_summary)

    manual_response_delay_days = int(params.get("manual_response_delay_days", 1))
    agent_response_delay_days = int(params.get("agent_response_delay_days", 0))

    expedite_option = _get_expedite_option(case_summary)
    expedite_time_saved_days = int(expedite_option.get("estimated_time_saved_days", 0)) if expedite_option else 0

    # Without agent: slower response, no mitigation applied immediately
    without_agent_delay_days = original_delay_days + manual_response_delay_days
    without_agent_gap_days = _compute_gap_from_delay(without_agent_delay_days, inventory_days)

    # With agent: fast response + expedite if available
    with_agent_delay_days = max(0, original_delay_days + agent_response_delay_days - expedite_time_saved_days)
    with_agent_gap_days = _compute_gap_from_delay(with_agent_delay_days, inventory_days)

    daily_usage_units = _get_daily_usage_units(case_summary)
    selling_price_per_unit_cad = float(params["selling_price_per_unit_cad"])
    contribution_margin_per_unit_cad = float(params["contribution_margin_per_unit_cad"])
    sla_penalty_per_unit_cad = float(params["sla_penalty_per_unit_cad"])
    line_downtime_cost_per_day_cad = float(params["line_downtime_cost_per_day_cad"])
    committed_units_in_window = max(1, int(params["committed_units_in_window"]))

    revenue_without = without_agent_gap_days * daily_usage_units * selling_price_per_unit_cad
    revenue_with = with_agent_gap_days * daily_usage_units * selling_price_per_unit_cad

    margin_without = without_agent_gap_days * daily_usage_units * contribution_margin_per_unit_cad
    margin_with = with_agent_gap_days * daily_usage_units * contribution_margin_per_unit_cad

    late_units_without = without_agent_gap_days * daily_usage_units
    late_units_with = with_agent_gap_days * daily_usage_units

    service_drop_without = (late_units_without / committed_units_in_window) * 100.0
    service_drop_with = (late_units_with / committed_units_in_window) * 100.0

    sla_without = late_units_without * sla_penalty_per_unit_cad
    sla_with = late_units_with * sla_penalty_per_unit_cad

    downtime_without = without_agent_gap_days * line_downtime_cost_per_day_cad
    downtime_with = with_agent_gap_days * line_downtime_cost_per_day_cad

    expedite_cost = 0.0
    expedite_meta = {"base_transport_cost_cad": 0.0, "expedite_quote_cad": 0.0, "expedite_premium_cad": 0.0, "expedite_premium_pct": 0.0}
    if expedite_option:
        expedite_meta = estimate_expedite_cost_cad(case_summary, params)
        expedite_cost = expedite_meta["expedite_premium_cad"]

    # No immediate inventory adjustment cost unless still needed
    suggested_extra_units_with = with_agent_gap_days * daily_usage_units
    inventory_adjustment_with = suggested_extra_units_with * float(params["unit_cost_cad"]) * float(
        params.get("carrying_cost_factor_for_window", 0.02)
    )

    total_without = downtime_without + sla_without
    total_with = downtime_with + sla_with + expedite_cost + inventory_adjustment_with

    return {
        "currency": "CAD",
        "without_agent": {
            "effective_delay_days": without_agent_delay_days,
            "stockout_gap_days": without_agent_gap_days,
            "revenue_at_risk_cad": round(revenue_without, 2),
            "margin_at_risk_cad": round(margin_without, 2),
            "service_level_drop_pct_points": round(service_drop_without, 2),
            "sla_penalty_cad": round(sla_without, 2),
            "downtime_cost_cad": round(downtime_without, 2),
            "total_cost_cad": round(total_without, 2),
        },
        "with_agent": {
            "effective_delay_days": with_agent_delay_days,
            "stockout_gap_days": with_agent_gap_days,
            "revenue_at_risk_cad": round(revenue_with, 2),
            "margin_at_risk_cad": round(margin_with, 2),
            "service_level_drop_pct_points": round(service_drop_with, 2),
            "sla_penalty_cad": round(sla_with, 2),
            "downtime_cost_cad": round(downtime_with, 2),
            "expedite_cost_cad": round(expedite_cost, 2),
            "inventory_adjustment_cost_cad": round(inventory_adjustment_with, 2),
            "total_cost_cad": round(total_with, 2),
            "expedite_premium_pct": round(expedite_meta["expedite_premium_pct"], 2),
        },
        "revenue_loss_prevented_cad": round(revenue_without - revenue_with, 2),
        "service_level_protection_pct_points": round(service_drop_without - service_drop_with, 2),
        "cost_optimization_cad": round(total_without - total_with, 2),
        "operational_continuity_improvement_days": int(without_agent_gap_days - with_agent_gap_days),
    }