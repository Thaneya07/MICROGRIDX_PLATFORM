export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

/** Normalize a power value (W) to [0, 1] against a reference maximum, for driving visual intensity. */
export function normalizePower(watts: number, referenceMaxW: number): number {
  if (referenceMaxW <= 0) return 0;
  return clamp(watts / referenceMaxW, 0, 1);
}

export const REFERENCE_MAX_SOLAR_W = 4000;
export const REFERENCE_MAX_CONSUMPTION_W = 2500;
export const REFERENCE_MAX_GRID_W = 2500;
export const REFERENCE_BATTERY_POWER_W = 1000;
