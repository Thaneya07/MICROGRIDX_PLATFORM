/** Mirrors app/schemas/analytics.py EnergySummaryResponse (Step 4). Used only for the read-only analytics overlay. */
export interface EnergySummaryResponse {
  start: string;
  end: string;
  reading_count: number;
  total_consumption_wh: number;
  total_generation_wh: number;
  solar_self_consumption_wh: number;
  grid_import_wh: number;
  grid_export_wh: number;
  peak_demand_w: number;
  average_demand_w: number;
  load_factor: number | null;
  renewable_contribution_pct: number | null;
  grid_dependency_pct: number | null;
  battery_charge_wh: number | null;
  battery_discharge_wh: number | null;
  battery_throughput_wh: number | null;
}
