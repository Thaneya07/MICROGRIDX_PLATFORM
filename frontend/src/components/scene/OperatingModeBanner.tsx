import type { OperatingMode } from "@/types/decision";
import "./OperatingModeBanner.css";

export interface OperatingModeBannerProps {
  mode: OperatingMode | null;
  reason: string | null;
}

const MODE_META: Record<OperatingMode, { label: string; className: string }> = {
  NORMAL_MODE: { label: "NORMAL", className: "mgx-mode-banner--normal" },
  ECO_MODE: { label: "ECO", className: "mgx-mode-banner--eco" },
  EMERGENCY_MODE: { label: "EMERGENCY", className: "mgx-mode-banner--emergency" },
};

/**
 * The single most prominent status element on the page: the Decision
 * Engine's current operating-mode recommendation. Always shown as a
 * RECOMMENDATION, never as if the system had actually switched modes on
 * its own — see the reason text and the DecisionPanel's safety note for
 * the full boundary.
 */
export function OperatingModeBanner({ mode, reason }: OperatingModeBannerProps) {
  if (!mode) {
    return (
      <div className="mgx-mode-banner mgx-mode-banner--unknown">
        <span className="mgx-mode-banner-label">OPERATING MODE: UNKNOWN</span>
        <span className="mgx-mode-banner-reason">Run an optimization to get a recommendation.</span>
      </div>
    );
  }

  const meta = MODE_META[mode];
  return (
    <div className={`mgx-mode-banner ${meta.className}`}>
      <span className="mgx-mode-banner-tag">RECOMMENDED</span>
      <span className="mgx-mode-banner-label">{meta.label}_MODE</span>
      {reason && <span className="mgx-mode-banner-reason">{reason}</span>}
    </div>
  );
}
