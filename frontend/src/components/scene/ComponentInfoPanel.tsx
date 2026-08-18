import { Badge, Card, EmptyState } from "@/components/ui";
import type { SelectedComponent } from "./selection";

export interface ComponentInfoPanelProps {
  selected: SelectedComponent | null;
}

/** Shows telemetry for whatever component the user last clicked in the 3D scene. */
export function ComponentInfoPanel({ selected }: ComponentInfoPanelProps) {
  return (
    <Card>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
        <h3 style={{ fontSize: 14 }}>Selected component</h3>
        {selected && <Badge tone="accent">{selected.kind}</Badge>}
      </div>

      {!selected && (
        <EmptyState title="Nothing selected" description="Click a component in the 3D scene to inspect it." />
      )}

      {selected && (
        <div>
          <p style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>{selected.title}</p>
          <dl style={{ display: "flex", flexDirection: "column", gap: 6, margin: 0 }}>
            {selected.details.map((d) => (
              <div key={d.label} style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
                <dt style={{ color: "var(--color-text-muted)" }}>{d.label}</dt>
                <dd style={{ margin: 0, fontFamily: "var(--font-mono)" }}>{d.value}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}
    </Card>
  );
}
