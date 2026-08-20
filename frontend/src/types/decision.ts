/** Mirrors app/schemas/decision.py. RECOMMENDATION data only — never a control command. */

export type OptimizationStatus = "OPTIMAL" | "INFEASIBLE" | "SAFE_FALLBACK" | "ERROR";
export type BatteryAction = "CHARGE" | "DISCHARGE" | "IDLE";
export type ApprovalStatus = "PENDING" | "APPROVED" | "REJECTED";

export interface LoadRecommendation {
  load_id: string;
  load_name: string;
  action: string;
  reason: string;
  priority: number;
}

export interface ConstraintCheck {
  name: string;
  satisfied: boolean;
  detail: string;
}

export interface Decision {
  id: string;
  microgrid_id: string;
  created_at: string;
  source: "SIMULATED" | "HARDWARE";
  optimization_status: OptimizationStatus;

  horizon_start: string;
  horizon_end: string;
  interval_minutes: number;

  objective_value: number | null;

  recommended_battery_action: BatteryAction;
  recommended_battery_power_w: number | null;
  load_recommendations: LoadRecommendation[];

  expected_grid_import_wh: number | null;
  expected_grid_export_wh: number | null;
  expected_renewable_utilization_pct: number | null;
  expected_peak_w: number | null;

  constraints_checked: ConstraintCheck[];
  constraints_satisfied: boolean;

  explanation: string;
  recommendation_reason: string;

  fallback_used: boolean;
  fallback_reason: string | null;

  provenance: Record<string, unknown>;

  approval_status: ApprovalStatus;
  approved_at: string | null;

  safety_note: string;
}
