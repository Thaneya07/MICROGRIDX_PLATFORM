import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  Input,
  LoadingState,
  MetricCard,
  PageHeader,
  StatusIndicator,
} from "@/components/ui";
import { MicrogridScene } from "@/components/scene/MicrogridScene";
import { DataSourceBadge } from "@/components/scene/DataSourceBadge";
import { ForecastPanel } from "@/components/scene/ForecastPanel";
import { useTelemetryStream } from "@/hooks/useTelemetryStream";
import { useForecast } from "@/hooks/useForecast";
import { getBatteryFlowState, getGridFlowState, hasLiveData } from "@/components/scene/sceneMapping";
import "./VisualizationPage.css";

const BATTERY_LABEL: Record<string, string> = {
  charging: "Charging",
  discharging: "Discharging",
  idle: "Idle",
  unknown: "Unknown",
};

const GRID_LABEL: Record<string, string> = {
  importing: "Importing",
  exporting: "Exporting",
  balanced: "Balanced",
  unknown: "Unknown",
};

export function VisualizationPage() {
  const [microgridIdInput, setMicrogridIdInput] = useState("");
  const [activeMicrogridId, setActiveMicrogridId] = useState<string | null>(null);

  const stream = useTelemetryStream(activeMicrogridId);
  const demandForecast = useForecast(activeMicrogridId, "DEMAND");
  const solarForecast = useForecast(activeMicrogridId, "SOLAR_GENERATION");

  const connectionStatusTone =
    stream.status === "connected"
      ? "online"
      : stream.status === "fallback_polling"
        ? "warn"
        : stream.status === "error"
          ? "danger"
          : "offline";

  const connectionStatusLabel =
    stream.status === "connected"
      ? "Live (WebSocket)"
      : stream.status === "fallback_polling"
        ? "Live (REST fallback)"
        : stream.status === "connecting"
          ? "Connecting..."
          : stream.status === "reconnecting"
            ? "Reconnecting..."
            : stream.status === "error"
              ? "Stream error"
              : "Not connected";

  return (
    <div className="mgx-page mgx-viz-page">
      <PageHeader
        eyebrow="Phase 2, Step 6"
        title="Energy System Visualization"
        description="Interactive 3D view of the microgrid's physical energy system, driven by live (or simulated) telemetry. This is an observation view — it does not control any device."
      />

      <Card className="mgx-viz-controls">
        <Input
          label="Microgrid ID"
          placeholder="Paste a microgrid UUID (see README for how to create one)"
          value={microgridIdInput}
          onChange={(e) => setMicrogridIdInput(e.target.value)}
        />
        <Button
          onClick={() => setActiveMicrogridId(microgridIdInput.trim() || null)}
          disabled={!microgridIdInput.trim()}
        >
          Load scene
        </Button>
      </Card>

      {!activeMicrogridId && (
        <EmptyState
          title="No microgrid selected"
          description="Enter a microgrid ID above and click 'Load scene' to visualize its energy system."
        />
      )}

      {activeMicrogridId && stream.status === "connecting" && !stream.snapshot && (
        <LoadingState message="Connecting to live telemetry..." />
      )}

      {activeMicrogridId && stream.status === "error" && !stream.snapshot && (
        <ErrorState
          title="Could not load telemetry"
          description={stream.errorMessage ?? "The telemetry stream reported an error."}
          onRetry={stream.reconnect}
        />
      )}

      {activeMicrogridId && stream.snapshot && (
        <>
          <div className="mgx-viz-status-bar">
            <StatusIndicator status={connectionStatusTone} label={connectionStatusLabel} />
            <DataSourceBadge source={stream.snapshot.source} />
            <Badge tone="neutral">{stream.snapshot.name}</Badge>
            <span className="mgx-viz-updated">
              Updated {new Date(stream.snapshot.server_time).toLocaleTimeString()}
            </span>
          </div>

          {!hasLiveData(stream.snapshot) ? (
            <EmptyState
              title="No energy reading available"
              description={
                stream.snapshot.energy_reading_error ?? "This microgrid has no current energy reading yet."
              }
            />
          ) : (
            <div className="mgx-viz-layout">
              <div className="mgx-viz-scene">
                <MicrogridScene snapshot={stream.snapshot} />
              </div>

              <div className="mgx-viz-sidebar">
                <div className="mgx-viz-metrics">
                  <MetricCard
                    label="Consumption"
                    value={stream.snapshot.energy_reading!.consumption_w.toFixed(0)}
                    unit="W"
                  />
                  <MetricCard
                    label="Generation"
                    value={stream.snapshot.energy_reading!.generation_w.toFixed(0)}
                    unit="W"
                  />
                  <MetricCard
                    label="Battery"
                    value={
                      stream.snapshot.energy_reading!.battery_soc_percent !== null
                        ? stream.snapshot.energy_reading!.battery_soc_percent!.toFixed(0)
                        : "—"
                    }
                    unit="%"
                    trend={BATTERY_LABEL[getBatteryFlowState(stream.snapshot)]}
                  />
                  <MetricCard
                    label="Grid"
                    value={
                      getGridFlowState(stream.snapshot) === "importing"
                        ? stream.snapshot.energy_reading!.grid_import_w.toFixed(0)
                        : stream.snapshot.energy_reading!.grid_export_w.toFixed(0)
                    }
                    unit="W"
                    trend={GRID_LABEL[getGridFlowState(stream.snapshot)]}
                  />
                </div>

                <ForecastPanel title="Demand forecast (next 12h)" state={demandForecast} />
                <ForecastPanel title="Solar generation forecast (next 12h)" state={solarForecast} />
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
