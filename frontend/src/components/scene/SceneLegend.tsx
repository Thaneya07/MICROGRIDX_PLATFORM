import { Card } from "@/components/ui";

interface LegendEntry {
  color: string;
  label: string;
}

const ENTRIES: LegendEntry[] = [
  { color: "#f5a623", label: "Generation / grid import" },
  { color: "#2dd4bf", label: "Battery discharge / grid export" },
  { color: "#e7ecf2", label: "Consumption" },
  { color: "#5a6773", label: "Idle / offline" },
];

/** Static color-key for the 3D scene's flow lines and status indicators. */
export function SceneLegend() {
  return (
    <Card padded>
      <h3 style={{ fontSize: 13, marginBottom: 10, color: "var(--color-text-muted)" }}>Legend</h3>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {ENTRIES.map((entry) => (
          <div key={entry.label} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12 }}>
            <span
              style={{
                display: "inline-block",
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: entry.color,
                flexShrink: 0,
              }}
            />
            <span style={{ color: "var(--color-text-muted)" }}>{entry.label}</span>
          </div>
        ))}
      </div>
      <p style={{ fontSize: 11, color: "var(--color-text-faint)", marginTop: 10 }}>
        Click any component in the scene to inspect its current telemetry. Drag to orbit, scroll to zoom.
      </p>
    </Card>
  );
}
