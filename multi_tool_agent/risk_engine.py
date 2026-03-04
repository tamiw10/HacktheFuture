def assess_risk_logic(case_summary: dict) -> dict:
    score = 0
    reasons = []

    manufacturer = case_summary["manufacturer_profile"]
    inventory = case_summary["inventory"]
    shipment = case_summary["shipment"]
    part = case_summary["part"]
    mitigation_options = case_summary["mitigation_options"]

    inventory_days = inventory["days_remaining"]
    delay_days = shipment["delay_days"]

    # 1. Delay vs inventory gap
    if inventory_days < delay_days:
        gap = delay_days - inventory_days
        score += 40
        reasons.append(
            f"Inventory will run out before the delayed shipment arrives "
            f"({inventory_days} days remaining vs {delay_days}-day delay, gap of {gap} days)."
        )
    else:
        reasons.append(
            f"Current inventory buffer can absorb the delay "
            f"({inventory_days} days remaining vs {delay_days}-day delay)."
        )

    # 2. Part criticality
    if part["criticality"].lower() == "high":
        score += 15
        reasons.append("The affected part is high criticality.")

    # 3. Supplier concentration risk
    if manufacturer["supplier_concentration_risk"]["single_source"]:
        score += 15
        reasons.append("The manufacturer depends on a single source for this part.")
    else:
        score -= 5
        reasons.append("The manufacturer is not fully dependent on a single source.")

    # 4. Lean inventory policy
    if manufacturer["inventory_buffer_policy"]["lean_inventory_strategy"]:
        score += 10
        reasons.append("The manufacturer follows a lean inventory strategy, reducing buffer against disruptions.")
    else:
        score -= 5
        reasons.append("The manufacturer keeps a larger inventory buffer.")

    # 5. Customer SLA strictness
    if manufacturer["customer_service_levels"]["strict_sla"]:
        score += 10
        reasons.append("Strict customer service commitments increase the cost of delays.")
    else:
        score -= 5
        reasons.append("Customer service commitments are more flexible.")

    # 6. Lead-time sensitivity
    max_tolerable_delay = manufacturer["lead_time_sensitivity"]["max_tolerable_delay_days_for_critical_parts"]
    if delay_days > max_tolerable_delay:
        score += 10
        reasons.append(
            f"The delay exceeds the manufacturer's tolerable delay threshold for critical parts "
            f"({delay_days} days vs {max_tolerable_delay} days)."
        )
    else:
        score -= 5
        reasons.append(
            f"The delay is within the manufacturer's tolerable threshold for critical parts "
            f"({delay_days} days vs {max_tolerable_delay} days)."
        )

    # 7. Contract flexibility / alternate supplier
    alt_preapproved = manufacturer["contract_structures"]["alternate_supplier_preapproved"]
    backup_option_available = any(
        option["option_type"] == "backup_supplier" and option["available"]
        for option in mitigation_options
    )

    if alt_preapproved and backup_option_available:
        score -= 10
        reasons.append("A preapproved alternate supplier provides a fallback option.")
    else:
        score += 10
        reasons.append("No preapproved alternate supplier is available for rapid switching.")

    # Keep score in a clean range
    if score < 0:
        score = 0

    # Final risk level
    if score >= 80:
        risk_level = "critical"
    elif score >= 55:
        risk_level = "high"
    elif score >= 30:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "risk_score": score,
        "risk_level": risk_level,
        "reasons": reasons
    }