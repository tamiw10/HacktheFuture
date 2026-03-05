import json
from pathlib import Path
from .risk_engine import assess_risk_logic
from .perception import get_signals_for_shipment, get_recent_signals

from .metrics_engine import (
    compare_scenarios_with_without_agent,
    estimate_downtime_cost_cad,
    estimate_margin_at_risk_cad,
    estimate_revenue_at_risk_cad,
    estimate_service_level_impact,
    estimate_expedite_cost_cad,
    estimate_sla_penalty_cad,
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def _load_json(filename: str):
    with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


def get_manufacturer_profile(manufacturer_id: str) -> dict:
    profiles = _load_json("manufacturer_profiles.json")
    for profile in profiles:
        if profile["manufacturer_id"] == manufacturer_id:
            return profile
    return {"error": f"Manufacturer {manufacturer_id} not found."}


def get_inventory_status(plant_id: str, part_id: str) -> dict:
    inventory_data = _load_json("inventory.json")
    for item in inventory_data:
        if item["plant_id"] == plant_id and item["part_id"] == part_id:
            return item
    return {"error": f"Inventory for plant {plant_id} and part {part_id} not found."}


def get_shipment_status(shipment_id: str) -> dict:
    shipments = _load_json("shipments.json")
    for shipment in shipments:
        if shipment["shipment_id"] == shipment_id:
            return shipment
    return {"error": f"Shipment {shipment_id} not found."}


def get_part_data(part_id: str) -> dict:
    parts = _load_json("parts.json")
    for part in parts:
        if part["part_id"] == part_id:
            return part
    return {"error": f"Part {part_id} not found."}


def get_supplier_data(supplier_id: str) -> dict:
    suppliers = _load_json("suppliers.json")
    for supplier in suppliers:
        if supplier["supplier_id"] == supplier_id:
            return supplier
    return {"error": f"Supplier {supplier_id} not found."}


def get_disruption_signals(shipment_id: str | None = None, recent_limit: int = 10) -> dict:
    """
    Get disruption signals. If shipment_id is provided, returns signals affecting that shipment.
    Otherwise returns the most recent signals across the system.
    """
    if shipment_id:
        signals = get_signals_for_shipment(shipment_id)
        return {"shipment_id": shipment_id, "disruption_signals": signals}
    return {"disruption_signals": get_recent_signals(limit=recent_limit)}


def get_mitigation_options(part_id: str) -> list:
    options = _load_json("mitigation_options.json")
    return [option for option in options if option["part_id"] == part_id]


def get_business_parameters() -> dict:
    return _load_json("business_parameters.json")


def handle_disruption_signal(shipment_id: str) -> dict:
    shipment = get_shipment_status(shipment_id)
    if "error" in shipment:
        return shipment

    manufacturer_id = shipment.get("manufacturer_id")
    if not manufacturer_id:
        return {"error": f"No manufacturer linked to shipment {shipment_id}."}

    manufacturer_profile = get_manufacturer_profile(manufacturer_id)
    if "error" in manufacturer_profile:
        return manufacturer_profile

    risk_result = assess_risk(manufacturer_id, shipment_id)
    if "error" in risk_result:
        return risk_result

    case_summary = risk_result["case_summary"]
    part_id = case_summary["part"]["part_id"]

    escalation = draft_escalation_message(manufacturer_id, shipment_id)
    supplier_email = draft_supplier_email(manufacturer_id, shipment_id)
    reorder_suggestion = suggest_reorder_adjustment(manufacturer_id, shipment_id)
    approval_boundaries = get_human_approval_boundaries()
    similar_past_cases = get_similar_past_cases(part_id, limit=3)
    business_impact = calculate_business_impact(manufacturer_id, shipment_id)
    with_without_agent = compare_with_without_agent(manufacturer_id, shipment_id)

    risk_level = risk_result["risk_assessment"]["risk_level"]
    outcome = (
        f"Signal handled. Risk={risk_level}. "
        f"Escalation drafted. Supplier email drafted. Reorder suggestion generated."
    )

    log_result = log_disruption_case(manufacturer_id, shipment_id, outcome)

    return {
        "shipment_id": shipment_id,
        "manufacturer_id": manufacturer_id,
        "manufacturer_name": manufacturer_profile["name"],
        "risk_result": risk_result,
        "business_impact": business_impact,
        "with_without_agent": with_without_agent,
        "escalation_message": escalation,
        "supplier_email": supplier_email,
        "reorder_suggestion": reorder_suggestion,
        "human_approval_boundaries": approval_boundaries,
        "similar_past_cases": similar_past_cases,
        "log_result": log_result,
    }


def build_case_summary(manufacturer_id: str, shipment_id: str) -> dict:
    profile = get_manufacturer_profile(manufacturer_id)
    shipment = get_shipment_status(shipment_id)

    if "error" in profile:
        return profile
    if "error" in shipment:
        return shipment

    if shipment.get("manufacturer_id") != manufacturer_id:
        return {
            "error": (
                f"Shipment {shipment_id} does not belong to manufacturer {manufacturer_id}. "
                f"It belongs to {shipment.get('manufacturer_id')}."
            )
        }

    inventory = get_inventory_status(
        plant_id=shipment["destination_plant_id"],
        part_id=shipment["part_id"]
    )
    if "error" in inventory:
        return inventory

    part = get_part_data(shipment["part_id"])
    if "error" in part:
        return part

    supplier = get_supplier_data(shipment["supplier_id"])
    if "error" in supplier:
        return supplier

    mitigations = get_mitigation_options(shipment["part_id"])

    manufacturer_allows_backup = profile["contract_structures"]["alternate_supplier_preapproved"]

    filtered_mitigations = []
    for option in mitigations:
        option_copy = option.copy()

        if option["option_type"] == "backup_supplier" and not manufacturer_allows_backup:
            option_copy["available"] = False
            option_copy["unavailable_reason"] = "No preapproved alternate supplier for this manufacturer."

        filtered_mitigations.append(option_copy)

    params = get_business_parameters()
    exp_meta = estimate_expedite_cost_cad(
        {
            "shipment": shipment,
            "mitigation_options": filtered_mitigations,
            "inventory": inventory,
            "part": part,
        },
        params
    )

    for opt in filtered_mitigations:
        if opt.get("option_type") == "expedite_shipment":
            # Keep computed fields
            opt["computed_cost_increase_pct"] = exp_meta["expedite_premium_pct"]
            opt["computed_cost_increase_cad"] = exp_meta["expedite_premium_cad"]

            # ALSO overwrite legacy keys so the LLM doesn't use stale values
            opt["estimated_cost_increase_pct"] = exp_meta["expedite_premium_pct"]
            opt["estimated_cost_increase_cad"] = exp_meta["expedite_premium_cad"]

    # ALWAYS use the full signal records from disruption_signals.json
    disruption_signal_payload = get_disruption_signals(shipment_id=shipment_id)
    disruption_signals = disruption_signal_payload.get("disruption_signals", [])

    severity_rank = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    highest_severity = None
    highest_rank = 0
    total_estimated_delay_days = 0

    for signal in disruption_signals:
        sev = signal.get("severity", "low")
        rank = severity_rank.get(sev, 0)
        if rank > highest_rank:
            highest_rank = rank
            highest_severity = sev
        total_estimated_delay_days += int(signal.get("estimated_delay_days", 0))

    signal_summary = {
        "count": len(disruption_signals),
        "signal_types": sorted(
            {signal.get("signal_type", "unknown") for signal in disruption_signals}
        ),
        "highest_severity": highest_severity,
        "total_estimated_delay_days": total_estimated_delay_days,
    }

    signal_summary_text = (
        f"{signal_summary['count']} signal(s) detected; "
        f"types: {', '.join(signal_summary['signal_types']) if signal_summary['signal_types'] else 'none'}; "
        f"highest severity: {signal_summary['highest_severity'] or 'none'}; "
        f"total estimated delay: {signal_summary['total_estimated_delay_days']} days."
    )

    return {
        "manufacturer_profile": profile,
        "shipment": shipment,
        "inventory": inventory,
        "part": part,
        "supplier": supplier,
        "mitigation_options": filtered_mitigations,
        "disruption_signals": disruption_signals,
        "signal_summary": signal_summary,
        "signal_summary_text": signal_summary_text,
    }


def assess_risk(manufacturer_id: str, shipment_id: str) -> dict:
    case_summary = build_case_summary(manufacturer_id, shipment_id)
    if "error" in case_summary:
        return case_summary

    risk = assess_risk_logic(case_summary)
    return {
        "case_summary": case_summary,
        "risk_assessment": risk
    }


def draft_escalation_message(manufacturer_id: str, shipment_id: str) -> dict:
    result = assess_risk(manufacturer_id, shipment_id)
    if "error" in result:
        return result

    risk = result["risk_assessment"]
    case_summary = result["case_summary"]
    shipment = case_summary["shipment"]
    inventory = case_summary["inventory"]
    manufacturer = case_summary["manufacturer_profile"]
    part = case_summary["part"]

    risk_level = risk["risk_level"].capitalize()
    manufacturer_name = manufacturer["name"]
    part_name = part["part_name"]
    delay_days = shipment["delay_days"]
    inventory_days = inventory["days_remaining"]

    if risk["risk_level"] in ["low", "medium"]:
        message = (
            f"No escalation needed at this time. Shipment {shipment_id} for {part_name} "
            f"is delayed by {delay_days} days for {manufacturer_name}, but current inventory "
            f"covers {inventory_days} days and is sufficient to absorb the delay. "
            f"Recommend continued monitoring and contingency review if conditions worsen."
        )
    else:
        message = (
            f"Urgent: Shipment {shipment_id} for {part_name} is delayed by {delay_days} days "
            f"for {manufacturer_name}, while current inventory covers only {inventory_days} days. "
            f"This creates a {risk_level.lower()} risk of stockout and production disruption. "
            f"Recommend immediate review by procurement and operations leadership, with expedited "
            f"shipment action prioritized to reduce disruption risk."
        )

    return {"message": message}


def draft_supplier_email(manufacturer_id: str, shipment_id: str) -> dict:
    result = assess_risk(manufacturer_id, shipment_id)
    if "error" in result:
        return result

    risk = result["risk_assessment"]
    case_summary = result["case_summary"]

    shipment = case_summary["shipment"]
    inventory = case_summary["inventory"]
    manufacturer = case_summary["manufacturer_profile"]
    part = case_summary["part"]

    supplier = case_summary.get("supplier", {})
    supplier_name = supplier.get("supplier_name", shipment.get("supplier_id", "the supplier"))
    manufacturer_name = manufacturer["name"]
    part_name = part["part_name"]
    shipment_id_value = shipment["shipment_id"]
    delay_days = shipment["delay_days"]
    inventory_days = inventory["days_remaining"]
    risk_level = risk["risk_level"].capitalize()
    approval = evaluate_human_approval("draft_supplier_email")

    if risk["risk_level"] in ["high", "critical"]:
        subject = f"Urgent update requested: {shipment_id_value} delay impacting {manufacturer_name}"
    else:
        subject = f"Update requested: {shipment_id_value} delay affecting {manufacturer_name}"

    if risk["risk_level"] in ["high", "critical"]:
        body = (
            f"Hello {supplier_name} team,\n\n"
            f"We are reaching out regarding shipment {shipment_id_value} for {part_name}. "
            f"Our records indicate a current delay of {delay_days} days.\n\n"
            f"This shipment supports {manufacturer_name}, where current inventory covers only "
            f"{inventory_days} days. Based on our assessment, this creates a {risk_level.lower()} "
            f"operational risk due to possible stockout and production disruption.\n\n"
            f"Please confirm the following as soon as possible:\n"
            f"1. Updated ETA for shipment {shipment_id_value}\n"
            f"2. Root cause of the delay\n"
            f"3. Whether any partial shipment, rerouting, or expedited recovery options are available\n"
            f"4. Recommended next steps from your side to reduce further disruption\n\n"
            f"We would appreciate a prompt update so our procurement and operations teams can finalize mitigation actions.\n\n"
            f"Best regards,\n"
            f"Supply Chain Risk Team"
        )
    else:
        body = (
            f"Hello {supplier_name} team,\n\n"
            f"We are following up on shipment {shipment_id_value} for {part_name}. "
            f"Our records indicate a current delay of {delay_days} days.\n\n"
            f"At the moment, {manufacturer_name} has sufficient inventory coverage ({inventory_days} days remaining), "
            f"so the immediate operational risk is assessed as {risk_level.lower()}. "
            f"However, we would appreciate an updated ETA and any relevant context on the delay so we can continue monitoring the situation.\n\n"
            f"Please let us know:\n"
            f"1. Updated ETA for shipment {shipment_id_value}\n"
            f"2. Root cause of the delay\n"
            f"3. Whether there is any risk of further extension\n\n"
            f"Thank you for your support.\n\n"
            f"Best regards,\n"
            f"Supply Chain Risk Team"
        )

    return {
        "subject": subject,
        "body": body,
        "approval_required": approval["requires_human_approval"],
        "approval_note": approval["reason"]
    }


def identify_affected_manufacturer(shipment_id: str) -> dict:
    shipment = get_shipment_status(shipment_id)
    if "error" in shipment:
        return shipment

    manufacturer_id = shipment.get("manufacturer_id")
    if not manufacturer_id:
        return {"error": f"No manufacturer linked to shipment {shipment_id}."}

    profile = get_manufacturer_profile(manufacturer_id)
    if "error" in profile:
        return profile

    return {
        "shipment_id": shipment_id,
        "manufacturer_id": manufacturer_id,
        "manufacturer_name": profile["name"]
    }


# Additional tools for advanced mitigation analysis and human approval workflow
def get_approval_policy(action_type: str) -> dict:
    policies = _load_json("approval_policy.json")
    for policy in policies:
        if policy["action_type"] == action_type:
            return policy
    return {"error": f"Approval policy for {action_type} not found."}


def evaluate_human_approval(action_type: str) -> dict:
    policy = get_approval_policy(action_type)
    if "error" in policy:
        return policy

    return {
        "action_type": action_type,
        "auto_allowed": policy["auto_allowed"],
        "requires_human_approval": policy["requires_human_approval"],
        "reason": policy["reason"]
    }


def get_human_approval_boundaries() -> dict:
    actions = [
        "draft_escalation_message",
        "draft_supplier_email",
        "suggest_reorder_adjustment",
        "switch_supplier",
        "approve_expedite_spend",
    ]

    summary = {}
    for action in actions:
        summary[action] = evaluate_human_approval(action)

    return summary


# Example of an additional tool that could be used for more advanced mitigation analysis
def suggest_reorder_adjustment(manufacturer_id: str, shipment_id: str) -> dict:
    result = assess_risk(manufacturer_id, shipment_id)
    if "error" in result:
        return result

    case_summary = result["case_summary"]
    risk = result["risk_assessment"]

    shipment = case_summary["shipment"]
    inventory = case_summary["inventory"]
    part = case_summary["part"]
    mitigation_options = case_summary["mitigation_options"]

    daily_usage_units = part.get("daily_usage_units", 0)
    delay_days = shipment["delay_days"]
    inventory_days = inventory["days_remaining"]

    # Original stockout gap without mitigation
    original_stockout_gap_days = max(0, delay_days - inventory_days)

    # Look for expedite option
    expedite_option = None
    for option in mitigation_options:
        if option.get("option_type") == "expedite_shipment" and option.get("available"):
            expedite_option = option
            break

    expedited_delay_days = delay_days
    expedited_stockout_gap_days = original_stockout_gap_days

    if expedite_option:
        time_saved = expedite_option.get("estimated_time_saved_days", 0)
        expedited_delay_days = max(0, delay_days - time_saved)
        expedited_stockout_gap_days = max(0, expedited_delay_days - inventory_days)

    suggested_extra_units = original_stockout_gap_days * daily_usage_units
    contingency_units = original_stockout_gap_days * daily_usage_units

    if original_stockout_gap_days == 0:
        recommendation = (
            "No reorder adjustment is immediately required. Current inventory is sufficient to absorb the current delay. "
            "Continue monitoring and reassess if disruption signals worsen."
        )
    elif expedite_option and expedited_stockout_gap_days == 0:
        recommendation = (
            f"No immediate reorder adjustment is required if expedited shipment is approved and executed successfully, "
            f"since expediting reduces the delay from {delay_days} days to {expedited_delay_days} days and removes the immediate stockout gap. "
            f"However, because this creates no safety buffer, a contingency plan should be prepared to build or reallocate "
            f"approximately {contingency_units} units of {part['part_name']} if the shipment slips further or expedite approval is delayed."
        )
    else:
        recommendation = (
            f"Recommend a temporary reorder adjustment to cover an estimated {original_stockout_gap_days}-day stockout gap. "
            f"Based on daily usage of {daily_usage_units} units, this suggests building or reallocating approximately "
            f"{suggested_extra_units} additional units of {part['part_name']} if feasible."
        )

    approval = evaluate_human_approval("suggest_reorder_adjustment")

    return {
        "part_id": part["part_id"],
        "part_name": part["part_name"],
        "risk_level": risk["risk_level"],
        "delay_days": delay_days,
        "inventory_days_remaining": inventory_days,
        "original_stockout_gap_days": original_stockout_gap_days,
        "expedited_delay_days": expedited_delay_days,
        "expedited_stockout_gap_days": expedited_stockout_gap_days,
        "daily_usage_units": daily_usage_units,
        "suggested_extra_units": suggested_extra_units,
        "recommendation": recommendation,
        "approval_required": approval["requires_human_approval"],
        "approval_note": approval["reason"]
    }


def calculate_business_impact(manufacturer_id: str, shipment_id: str) -> dict:
    result = assess_risk(manufacturer_id, shipment_id)
    if "error" in result:
        return result

    case_summary = result["case_summary"]
    params = get_business_parameters()

    revenue_at_risk_cad = estimate_revenue_at_risk_cad(case_summary, params, use_mitigation=False)
    margin_at_risk_cad = estimate_margin_at_risk_cad(case_summary, params, use_mitigation=False)
    service_level = estimate_service_level_impact(case_summary, params, use_mitigation=False)
    expedite_cost = estimate_expedite_cost_cad(case_summary, params)
    sla_penalty_cad = estimate_sla_penalty_cad(case_summary, params, use_mitigation=False)
    downtime_cost_cad = estimate_downtime_cost_cad(case_summary, params, use_mitigation=False)

    return {
        "currency": "CAD",
        "revenue_at_risk_cad": round(revenue_at_risk_cad, 2),
        "margin_at_risk_cad": round(margin_at_risk_cad, 2),
        "service_level_drop_pct_points": round(service_level["service_level_drop_pct_points"], 2),
        "late_units": service_level["late_units"],
        "expedite_cost_meta": expedite_cost,
        "sla_penalty_cad": round(sla_penalty_cad, 2),
        "downtime_cost_cad": round(downtime_cost_cad, 2),
    }


def compare_with_without_agent(manufacturer_id: str, shipment_id: str) -> dict:
    result = assess_risk(manufacturer_id, shipment_id)
    if "error" in result:
        return result

    case_summary = result["case_summary"]
    params = get_business_parameters()

    comparison = compare_scenarios_with_without_agent(case_summary, params)
    return comparison


# Additional tools for disruption case logging and historical analysis
def get_disruption_history(limit: int = 10) -> dict:
    history = _load_json("disruption_history.json")
    return {"history": history[-limit:]}


def log_disruption_case(manufacturer_id: str, shipment_id: str, outcome: str) -> dict:
    history_path = DATA_DIR / "disruption_history.json"
    history = _load_json("disruption_history.json")

    risk_result = assess_risk(manufacturer_id, shipment_id)
    if "error" in risk_result:
        return risk_result

    case_summary = risk_result["case_summary"]
    risk = risk_result["risk_assessment"]

    entry = {
        "manufacturer_id": manufacturer_id,
        "shipment_id": shipment_id,
        "part_id": case_summary["part"]["part_id"],
        "risk_level": risk["risk_level"],
        "signal_summary": case_summary.get("signal_summary", {}),
        "outcome": outcome
    }

    history.append(entry)

    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    return {"message": "Disruption case logged successfully.", "entry": entry}


def get_similar_past_cases(part_id: str, limit: int = 3) -> dict:
    history = _load_json("disruption_history.json")
    matches = [entry for entry in history if entry.get("part_id") == part_id]
    return {"similar_cases": matches[-limit:]}