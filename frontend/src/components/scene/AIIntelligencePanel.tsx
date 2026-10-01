import { useEffect, useState } from "react";

import {
  Badge,
  Button,
  Card,
  ErrorState,
  LoadingState,
  MetricCard,
} from "@/components/ui";


const API_BASE =
  import.meta.env.VITE_API_URL ??
  "http://127.0.0.1:8000";


type ModelInfo = {
  demand: {
    model: string;
    feature_count: number;
  };
  solar: {
    model: string;
    feature_count: number;
  };
};


type BatteryResult = {
  soh_percent: number;
  rul_cycles: number;
  battery_status: string;
  risk_score: number;
  failure_probability_percent: number;
  thermal_risk: string;
  efficiency_score: number;
  maintenance_recommendation: string;
};


type FaultResult = {
  fault_class: string;
  description: string;
  confidence_percent: number;
  system_status: string;
  severity: string;
  recommendation: string;
  model: string;
};


type DecisionResult = {
  energy_mode: string;
  battery_action: string;
  load_priority: string;
  system_health: string;
  recommendation: string;
  decision_status: string;
  review_required: boolean;
};


const SAMPLE_BATTERY = {
  ambient_temperature: 24.0,
  voltage_mean: 3.53,
  voltage_min: 2.61,
  voltage_max: 4.19,
  voltage_std: 0.236,
  current_mean: -1.82,
  current_min: -2.02,
  current_max: 0.001,
  current_std: 0.59,
  temperature_mean: 32.57,
  temperature_min: 24.33,
  temperature_max: 38.98,
  temperature_std: 3.49,
  duration_sec: 3690.234,
  current_load_mean: -1.81,
  voltage_load_mean: 2.40,
  discharge_cycle_index: 1,
};


const SAMPLE_FAULT = {
  EA: 4.23e10,
  EB: 4.84e9,
  EC: 1.52e10,
};


export function AIIntelligencePanel() {
  const [modelInfo, setModelInfo] =
    useState<ModelInfo | null>(null);

  const [battery, setBattery] =
    useState<BatteryResult | null>(null);

  const [fault, setFault] =
    useState<FaultResult | null>(null);

  const [decision, setDecision] =
    useState<DecisionResult | null>(null);

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);


  useEffect(() => {
    const loadModelInfo = async () => {
      try {
        const response = await fetch(
          `${API_BASE}/api/ai-forecasts/models`
        );

        if (!response.ok) {
          throw new Error(
            `Model API returned ${response.status}`
          );
        }

        const data =
          (await response.json()) as ModelInfo;

        setModelInfo(data);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load AI model information."
        );
      }
    };

    void loadModelInfo();
  }, []);


  const runValidation = async () => {
    setLoading(true);
    setError(null);

    try {
      // ------------------------------------------------------
      // Battery Health
      // ------------------------------------------------------

      const batteryResponse = await fetch(
        `${API_BASE}/api/battery-health/predict`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(
            SAMPLE_BATTERY
          ),
        }
      );

      if (!batteryResponse.ok) {
        throw new Error(
          `Battery Health API returned ${batteryResponse.status}`
        );
      }

      const batteryData =
        (await batteryResponse.json()) as BatteryResult;

      setBattery(batteryData);


      // ------------------------------------------------------
      // Fault Detection
      // ------------------------------------------------------

      const faultResponse = await fetch(
        `${API_BASE}/api/fault-detection/predict`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(
            SAMPLE_FAULT
          ),
        }
      );

      if (!faultResponse.ok) {
        throw new Error(
          `Fault Detection API returned ${faultResponse.status}`
        );
      }

      const faultData =
        (await faultResponse.json()) as FaultResult;

      setFault(faultData);


      // ------------------------------------------------------
      // AI Decision Fusion
      //
      // Demand / solar values here are explicitly a validation
      // scenario, not live sensor telemetry.
      // ------------------------------------------------------

      const decisionPayload = {
        demand_forecast_w: 1200,
        solar_forecast_w: 1800,

        battery_soh_percent:
          batteryData.soh_percent,

        battery_rul_cycles:
          batteryData.rul_cycles,

        battery_status:
          batteryData.battery_status,

        battery_risk_score:
          batteryData.risk_score,

        thermal_risk:
          batteryData.thermal_risk,

        fault_class:
          faultData.fault_class,

        fault_severity:
          faultData.severity,
      };


      const decisionResponse = await fetch(
        `${API_BASE}/api/ai-decision/generate`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(
            decisionPayload
          ),
        }
      );

      if (!decisionResponse.ok) {
        throw new Error(
          `AI Decision API returned ${decisionResponse.status}`
        );
      }

      const decisionData =
        (await decisionResponse.json()) as DecisionResult;

      setDecision(decisionData);

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "AI validation failed."
      );
    } finally {
      setLoading(false);
    }
  };


  return (
    <Card>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 12,
        }}
      >
        <div>
          <h3 style={{ fontSize: 14, margin: 0 }}>
            AI Intelligence
          </h3>

          <p
            style={{
              margin: "4px 0 0",
              fontSize: 11,
              color: "var(--color-text-muted)",
            }}
          >
            Trained model status and validation inference
          </p>
        </div>

        <Badge tone="accent">
          AI
        </Badge>
      </div>


      {/* ======================================================
          MODEL STATUS
          ====================================================== */}

      {modelInfo ? (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 8,
            marginBottom: 12,
          }}
        >
          <MetricCard
            label="Demand model"
            value="Enhanced RF"
          />

          <MetricCard
            label="Solar model"
            value="RF"
          />

          <MetricCard
            label="Demand features"
            value={String(
              modelInfo.demand.feature_count
            )}
          />

          <MetricCard
            label="Solar features"
            value={String(
              modelInfo.solar.feature_count
            )}
          />
        </div>
      ) : !error ? (
        <LoadingState
          message="Loading AI model information..."
        />
      ) : null}


      {/* ======================================================
          VALIDATION NOTICE
          ====================================================== */}

      <div
        style={{
          padding: 10,
          marginBottom: 12,
          borderRadius: 8,
          background:
            "var(--color-surface-muted)",
          fontSize: 11,
          color: "var(--color-text-muted)",
          lineHeight: 1.5,
        }}
      >
        Validation mode uses prepared model-test inputs.
        These results are not presented as live ESP32
        telemetry.
      </div>


      <Button
        size="sm"
        variant="secondary"
        onClick={runValidation}
        disabled={loading}
      >
        {loading
          ? "Running AI models..."
          : "Run AI validation"}
      </Button>


      {error && (
        <div style={{ marginTop: 10 }}>
          <ErrorState
            title="AI validation unavailable"
            description={error}
          />
        </div>
      )}


      {/* ======================================================
          BATTERY HEALTH
          ====================================================== */}

      {battery && (
        <div
          style={{
            marginTop: 16,
            paddingTop: 14,
            borderTop:
              "1px solid var(--color-border)",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 8,
            }}
          >
            <strong style={{ fontSize: 12 }}>
              Battery Health
            </strong>

            <Badge tone="online">
              XGBoost
            </Badge>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns:
                "1fr 1fr",
              gap: 8,
            }}
          >
            <MetricCard
              label="SOH"
              value={
                battery.soh_percent.toFixed(2)
              }
              unit="%"
            />

            <MetricCard
              label="RUL"
              value={
                battery.rul_cycles.toFixed(0)
              }
              unit="cycles"
            />

            <MetricCard
              label="Risk"
              value={
                battery.risk_score.toFixed(1)
              }
            />

            <MetricCard
              label="Efficiency"
              value={
                battery.efficiency_score.toFixed(1)
              }
              unit="%"
            />
          </div>

          <div
            style={{
              display: "flex",
              gap: 6,
              flexWrap: "wrap",
              marginTop: 8,
            }}
          >
            <Badge tone="online">
              {battery.battery_status}
            </Badge>

            <Badge tone="neutral">
              Thermal: {battery.thermal_risk}
            </Badge>
          </div>

          <p
            style={{
              margin: "8px 0 0",
              fontSize: 11,
              color:
                "var(--color-text-muted)",
            }}
          >
            {battery.maintenance_recommendation}
          </p>
        </div>
      )}


      {/* ======================================================
          FAULT DETECTION
          ====================================================== */}

      {fault && (
        <div
          style={{
            marginTop: 16,
            paddingTop: 14,
            borderTop:
              "1px solid var(--color-border)",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 8,
            }}
          >
            <strong style={{ fontSize: 12 }}>
              Fault Detection
            </strong>

            <Badge tone="online">
              {fault.model}
            </Badge>
          </div>

          <div
            style={{
              display: "flex",
              gap: 6,
              flexWrap: "wrap",
            }}
          >
            <Badge
              tone={
                fault.severity === "HIGH"
                  ? "danger"
                  : fault.severity === "MEDIUM"
                    ? "warn"
                    : "online"
              }
            >
              {fault.fault_class}
            </Badge>

            <Badge tone="neutral">
              Confidence:{" "}
              {fault.confidence_percent.toFixed(1)}%
            </Badge>
          </div>

          <p
            style={{
              margin: "8px 0 0",
              fontSize: 11,
              color:
                "var(--color-text-muted)",
            }}
          >
            {fault.description}
          </p>
        </div>
      )}


      {/* ======================================================
          DECISION FUSION
          ====================================================== */}

      {decision && (
        <div
          style={{
            marginTop: 16,
            paddingTop: 14,
            borderTop:
              "1px solid var(--color-border)",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 8,
            }}
          >
            <strong style={{ fontSize: 12 }}>
              AI Decision Fusion
            </strong>

            <Badge tone="accent">
              REVIEW
            </Badge>
          </div>

          <div
            style={{
              display: "flex",
              gap: 6,
              flexWrap: "wrap",
              marginBottom: 8,
            }}
          >
            <Badge tone="online">
              {decision.energy_mode}
            </Badge>

            <Badge tone="neutral">
              {decision.battery_action}
            </Badge>

            <Badge tone="neutral">
              {decision.system_health}
            </Badge>
          </div>

          <p
            style={{
              margin: 0,
              fontSize: 11,
              color:
                "var(--color-text-muted)",
              lineHeight: 1.5,
            }}
          >
            {decision.recommendation}
          </p>

          <p
            style={{
              margin:
                "8px 0 0",
              fontSize: 10,
              color:
                "var(--color-text-faint)",
            }}
          >
            Status: {decision.decision_status}
            {" · "}
            Human review:{" "}
            {decision.review_required
              ? "required"
              : "not required"}
          </p>
        </div>
      )}
    </Card>
  );
}