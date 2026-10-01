from __future__ import annotations

from typing import Any


# ============================================================
# AI DECISION FUSION
# ============================================================

def generate_ai_decision(
    demand_forecast_w: float,
    solar_forecast_w: float,
    battery_soh_percent: float,
    battery_rul_cycles: float,
    battery_status: str,
    battery_risk_score: float,
    thermal_risk: str,
    fault_class: str,
    fault_severity: str,
) -> dict[str, Any]:
    """
    Combine Demand Forecasting, Solar Forecasting,
    Battery Health, and Fault Detection into a single
    decision-support recommendation.

    This layer does not directly actuate physical hardware.
    """

    demand = max(0.0, float(demand_forecast_w))
    solar = max(0.0, float(solar_forecast_w))

    soh = float(battery_soh_percent)
    rul = max(0.0, float(battery_rul_cycles))
    risk = float(battery_risk_score)

    battery_status = str(
        battery_status
    ).upper()

    thermal_risk = str(
        thermal_risk
    ).upper()

    fault_class = str(
        fault_class
    )

    fault_severity = str(
        fault_severity
    ).upper()

    # --------------------------------------------------------
    # Net energy
    # --------------------------------------------------------

    net_energy_w = solar - demand

    renewable_coverage_percent = (
        solar / demand * 100.0
        if demand > 0
        else 0.0
    )

    # --------------------------------------------------------
    # Default state
    # --------------------------------------------------------

    energy_mode = "NORMAL_MODE"
    battery_action = "IDLE"
    load_priority = "NORMAL_LOAD"
    system_health = "HEALTHY"
    recommendation = (
        "Continue normal energy management."
    )

    reasons = []

    # ========================================================
    # FAULT OVERRIDE
    # ========================================================

    if fault_severity == "HIGH":

        energy_mode = "EMERGENCY_MODE"
        battery_action = "IDLE"
        load_priority = "CRITICAL_LOAD_ONLY"
        system_health = "FAULT_DETECTED"

        recommendation = (
            f"Fault '{fault_class}' detected. "
            "Prioritize critical loads and require "
            "fault investigation before normal operation."
        )

        reasons.append(
            "High-severity electrical fault detected."
        )

    # ========================================================
    # THERMAL OVERRIDE
    # ========================================================

    elif thermal_risk == "HIGH":

        energy_mode = "EMERGENCY_MODE"
        battery_action = "IDLE"
        load_priority = "CRITICAL_LOAD_ONLY"
        system_health = "THERMAL_WARNING"

        recommendation = (
            "High thermal risk detected. Reduce battery "
            "stress and inspect operating temperature."
        )

        reasons.append(
            "Battery thermal risk is high."
        )

    # ========================================================
    # CRITICAL BATTERY
    # ========================================================

    elif (
        battery_status == "CRITICAL"
        or soh < 70.0
        or rul <= 10.0
    ):

        energy_mode = "EMERGENCY_MODE"
        load_priority = "CRITICAL_LOAD_ONLY"
        system_health = "BATTERY_CRITICAL"

        if net_energy_w >= 0:
            battery_action = "CHARGE"
            recommendation = (
                "Battery health is critical. Use available "
                "renewable surplus conservatively and "
                "prioritize critical loads."
            )
        else:
            battery_action = "IDLE"
            recommendation = (
                "Battery health is critical and forecast "
                "energy is insufficient. Preserve battery "
                "energy and prioritize critical loads."
            )

        reasons.append(
            "Battery health or remaining useful life is critical."
        )

    # ========================================================
    # WARNING BATTERY
    # ========================================================

    elif (
        battery_status == "WARNING"
        or soh < 80.0
        or rul <= 20.0
        or risk >= 50.0
    ):

        energy_mode = "ECO_MODE"
        system_health = "BATTERY_WARNING"

        if net_energy_w > 0:
            battery_action = "CHARGE"

            recommendation = (
                "Renewable energy exceeds forecast demand. "
                "Use the surplus for controlled battery charging."
            )

        elif net_energy_w < 0:
            battery_action = "DISCHARGE"
            load_priority = "PRIORITIZED_LOAD"

            recommendation = (
                "Forecast demand exceeds renewable generation. "
                "Use controlled battery discharge while "
                "protecting battery health."
            )

        reasons.append(
            "Battery health indicates increased degradation risk."
        )

    # ========================================================
    # NORMAL OPERATION
    # ========================================================

    else:

        if solar > demand * 1.10:

            energy_mode = "NORMAL_MODE"
            battery_action = "CHARGE"
            system_health = "HEALTHY"

            recommendation = (
                "Forecast renewable generation exceeds demand. "
                "Use surplus energy for battery charging."
            )

            reasons.append(
                "Renewable surplus forecast."
            )

        elif solar < demand * 0.90:

            energy_mode = "ECO_MODE"
            battery_action = "DISCHARGE"
            load_priority = "PRIORITIZED_LOAD"
            system_health = "HEALTHY"

            recommendation = (
                "Forecast demand exceeds renewable generation. "
                "Use battery support while prioritizing loads."
            )

            reasons.append(
                "Renewable generation deficit forecast."
            )

        else:

            energy_mode = "NORMAL_MODE"
            battery_action = "IDLE"
            system_health = "HEALTHY"

            recommendation = (
                "Forecast generation and demand are approximately "
                "balanced. Maintain normal operation."
            )

            reasons.append(
                "Generation and demand are approximately balanced."
            )

    # ========================================================
    # ADDITIONAL HEALTH INFORMATION
    # ========================================================

    if risk >= 70.0:
        reasons.append(
            "Battery risk score is high."
        )

    if rul <= 20.0:
        reasons.append(
            "Predicted remaining useful life is low."
        )

    # --------------------------------------------------------
    # Return unified decision
    # --------------------------------------------------------

    return {
        "energy_mode": energy_mode,

        "battery_action": battery_action,

        "load_priority": load_priority,

        "system_health": system_health,

        "recommendation": recommendation,

        "decision_status": "PENDING_REVIEW",

        "review_required": True,

        "inputs": {
            "demand_forecast_w": round(
                demand,
                3,
            ),

            "solar_forecast_w": round(
                solar,
                3,
            ),

            "net_energy_w": round(
                net_energy_w,
                3,
            ),

            "renewable_coverage_percent": round(
                renewable_coverage_percent,
                3,
            ),

            "battery_soh_percent": round(
                soh,
                3,
            ),

            "battery_rul_cycles": round(
                rul,
                3,
            ),

            "battery_risk_score": round(
                risk,
                3,
            ),

            "thermal_risk": thermal_risk,

            "fault_class": fault_class,

            "fault_severity": fault_severity,
        },

        "reasons": reasons,
    }