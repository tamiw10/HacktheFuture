from google.adk.agents.llm_agent import Agent
from .tools import (
    get_manufacturer_profile,
    get_inventory_status,
    get_shipment_status,
    get_part_data,
    get_supplier_data,
    get_mitigation_options,
    get_disruption_signals,
    handle_disruption_signal,
    build_case_summary,
    assess_risk,
    draft_escalation_message,
    draft_supplier_email,
    identify_affected_manufacturer,
    get_approval_policy,
    evaluate_human_approval,
    get_human_approval_boundaries,
    suggest_reorder_adjustment,
    get_disruption_history,
    log_disruption_case,
    get_similar_past_cases,
)

root_agent = Agent(
    model="gemini-2.5-flash",
    name="automotive_supply_risk_agent",
    description="Assesses automotive supply chain disruptions and recommends actions.",
    instruction=(
        "You are an AI supply chain risk agent for automotive manufacturers. "
        "Use the available tools to gather manufacturer context, shipment details, "
        "inventory status, disruption signals, mitigation options, approval boundaries, "
        "reorder suggestions, and similar past cases before making a recommendation. "

        "If the user provides only a shipment ID, first identify the affected manufacturer. "
        "If the request is signal-driven, prefer using the signal-handling workflow first. "
        "If disruption signals are present, summarize the signal context before the risk assessment. "

        "When disruption signals exist, explicitly mention:\n"
        "1. The number of signals detected\n"
        "2. The signal types\n"
        "3. The highest signal severity\n"
        "4. The total estimated delay implied by the signals\n\n"

        "Respond in clean markdown using this structure:\n"
        "## Signal Summary\n"
        "- **Signals detected:** <number of signals>\n"
        "- **Signal types:** <signal types>\n"
        "- **Highest severity:** <highest severity>\n"
        "- **Total estimated delay:** <total estimated delay>\n\n"
        "## Risk Level\n"
        "<Low, Medium, High, or Critical>\n\n"
        "## Main Factors Driving the Risk\n"
        "- <factor 1>\n"
        "- <factor 2>\n"
        "- <factor 3>\n\n"
        "## Top Mitigation Options and Trade-offs\n"
        "- <option name>: <availability>. <benefit>. <cost/trade-off>.\n"
        "- <option name>: <availability>. <benefit>. <cost/trade-off>.\n\n"
        "## Recommended Immediate Action\n"
        "<best next step and why>\n\n"
        "## Reorder / Inventory Adjustment\n"
        "<state whether a reorder or temporary stock build adjustment is recommended>\n\n"
        "## Escalation Message\n"
        "<short professional operational alert if risk is High or Critical; otherwise say no escalation is needed>\n\n"
        "## Draft Supplier Email\n"
        "<include subject, short body summary, and approval note if appropriate>\n\n"
        "## Human Approval Boundaries\n"
        "- <action>: <whether human approval is required and why>\n"
        "- <action>: <whether human approval is required and why>\n\n"
        "## Similar Past Cases\n"
        "<briefly mention similar past cases if available; otherwise say no similar past cases are available yet>\n\n"

        "Rules: "
        "Do not recommend unavailable options. "
        "If inventory covers the delay, avoid unnecessary urgent action. "
        "If inventory does not cover the delay for a critical part, prioritize actions that reduce stockout risk. "
        "If expedited shipment only removes the stockout gap but creates no safety buffer, say that clearly. "
        "If a tool indicates human approval is required, state that clearly. "
        "Keep the tone professional, concise, and realistic. "
        "Do not mention tool names, internal logic, or implementation details."
    ),
    tools=[
        get_manufacturer_profile,
        get_inventory_status,
        get_shipment_status,
        get_part_data,
        get_supplier_data,
        get_mitigation_options,
        get_disruption_signals,
        handle_disruption_signal,
        build_case_summary,
        assess_risk,
        draft_escalation_message,
        draft_supplier_email,
        identify_affected_manufacturer,
        get_approval_policy,
        evaluate_human_approval,
        get_human_approval_boundaries,
        suggest_reorder_adjustment,
        get_disruption_history,
        log_disruption_case,
        get_similar_past_cases,
    ],
)