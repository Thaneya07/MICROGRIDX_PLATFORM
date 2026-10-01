import {
  Card,
  ErrorState,
  EmptyState,
  LoadingState,
  Badge,
} from "@/components/ui";

import type { ForecastState } from "@/hooks/useForecast";


export interface ForecastPanelProps {
  title: string;
  state: ForecastState;
}


interface ForecastChartProps {
  state: ForecastState;
}


function ForecastChart({
  state,
}: ForecastChartProps) {

  const points =
    state.forecast?.points ?? [];

  if (points.length === 0) {
    return null;
  }


  const width = 760;
  const height = 240;

  const padding = {
    left: 46,
    right: 16,
    top: 20,
    bottom: 34,
  };


  const allValues = points.flatMap(
    (point) => [
      point.lower_95_w,
      point.upper_95_w,
      point.predicted_w,
    ],
  );


  let minValue = Math.min(
    ...allValues,
  );

  let maxValue = Math.max(
    ...allValues,
  );


  if (!Number.isFinite(minValue)) {
    minValue = 0;
  }

  if (!Number.isFinite(maxValue)) {
    maxValue = 1;
  }


  /*
   * Keep some visual breathing room.
   */
  const range =
    Math.max(
      1,
      maxValue - minValue,
    );

  minValue =
    Math.max(
      0,
      minValue - range * 0.08,
    );

  maxValue =
    maxValue + range * 0.08;


  const chartWidth =
    width -
    padding.left -
    padding.right;

  const chartHeight =
    height -
    padding.top -
    padding.bottom;


  const xForIndex = (
    index: number,
  ) => {
    if (points.length === 1) {
      return (
        padding.left +
        chartWidth / 2
      );
    }

    return (
      padding.left +
      (index /
        (points.length - 1)) *
        chartWidth
    );
  };


  const yForValue = (
    value: number,
  ) => {

    const ratio =
      (value - minValue) /
      (maxValue - minValue);

    return (
      padding.top +
      (1 - ratio) *
        chartHeight
    );
  };


  const predictedPath =
    points
      .map(
        (point, index) =>
          `${xForIndex(index)},${yForValue(
            point.predicted_w,
          )}`,
      )
      .join(" ");


  const upperPath =
    points
      .map(
        (point, index) =>
          `${xForIndex(index)},${yForValue(
            point.upper_95_w,
          )}`,
      )
      .join(" ");


  const lowerPath =
    [...points]
      .reverse()
      .map(
        (point, reverseIndex) => {

          const originalIndex =
            points.length -
            1 -
            reverseIndex;

          return `${xForIndex(
            originalIndex,
          )},${yForValue(
            point.lower_95_w,
          )}`;
        },
      )
      .join(" ");


  const uncertaintyPath =
    `${upperPath} ${lowerPath}`;


  const maxIndex =
    points.reduce(
      (
        bestIndex,
        point,
        index,
      ) =>
        point.predicted_w >
        points[bestIndex].predicted_w
          ? index
          : bestIndex,
      0,
    );


  const latestIndex =
    points.length - 1;


  const formatPower = (
    value: number,
  ) => {

    if (value >= 1000) {
      return `${(
        value / 1000
      ).toFixed(1)} kW`;
    }

    return `${value.toFixed(0)} W`;
  };


  const formatTime = (
    timestamp: string,
  ) =>
    new Date(
      timestamp,
    ).toLocaleTimeString(
      [],
      {
        hour: "2-digit",
        minute: "2-digit",
      },
    );


  const firstTime =
    formatTime(
      points[0].timestamp,
    );

  const middleTime =
    formatTime(
      points[
        Math.floor(
          points.length / 2,
        )
      ].timestamp,
    );

  const lastTime =
    formatTime(
      points[
        points.length - 1
      ].timestamp,
    );


  return (
    <div>

      {/* =====================================================
          SUMMARY METRICS
          ===================================================== */}

      <div
        style={{
          display: "grid",
          gridTemplateColumns:
            "repeat(3, 1fr)",
          gap: 8,
          marginBottom: 12,
        }}
      >

        <div
          style={{
            padding: 9,
            borderRadius: 8,
            background:
              "var(--color-surface-muted)",
          }}
        >
          <div
            style={{
              fontSize: 10,
              color:
                "var(--color-text-faint)",
            }}
          >
            Latest
          </div>

          <div
            style={{
              marginTop: 3,
              fontSize: 14,
              fontWeight: 600,
            }}
          >
            {formatPower(
              points[
                latestIndex
              ].predicted_w,
            )}
          </div>
        </div>


        <div
          style={{
            padding: 9,
            borderRadius: 8,
            background:
              "var(--color-surface-muted)",
          }}
        >
          <div
            style={{
              fontSize: 10,
              color:
                "var(--color-text-faint)",
            }}
          >
            Peak
          </div>

          <div
            style={{
              marginTop: 3,
              fontSize: 14,
              fontWeight: 600,
            }}
          >
            {formatPower(
              points[
                maxIndex
              ].predicted_w,
            )}
          </div>
        </div>


        <div
          style={{
            padding: 9,
            borderRadius: 8,
            background:
              "var(--color-surface-muted)",
          }}
        >
          <div
            style={{
              fontSize: 10,
              color:
                "var(--color-text-faint)",
            }}
          >
            Samples
          </div>

          <div
            style={{
              marginTop: 3,
              fontSize: 14,
              fontWeight: 600,
            }}
          >
            {points.length}
          </div>
        </div>

      </div>


      {/* =====================================================
          CHART
          ===================================================== */}

      <div
        style={{
          width: "100%",
          overflow: "hidden",
          borderRadius: 10,
          border:
            "1px solid var(--color-border)",
          background:
            "var(--color-surface-muted)",
        }}
      >

        <svg
          viewBox={`0 0 ${width} ${height}`}
          width="100%"
          height="240"
          preserveAspectRatio="none"
          role="img"
          aria-label="AI forecast chart"
        >

          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map(
            (ratio) => {

              const y =
                padding.top +
                ratio *
                  chartHeight;

              const value =
                maxValue -
                ratio *
                  (maxValue -
                    minValue);

              return (
                <g key={ratio}>

                  <line
                    x1={padding.left}
                    x2={
                      width -
                      padding.right
                    }
                    y1={y}
                    y2={y}
                    stroke="currentColor"
                    strokeOpacity={0.09}
                  />

                  <text
                    x={padding.left - 8}
                    y={y + 4}
                    textAnchor="end"
                    fontSize={10}
                    fill="currentColor"
                    opacity={0.55}
                  >
                    {formatPower(
                      value,
                    )}
                  </text>

                </g>
              );
            },
          )}


          {/* Uncertainty band */}

          <polygon
            points={uncertaintyPath}
            fill="currentColor"
            fillOpacity={0.08}
            stroke="none"
          />


          {/* Lower uncertainty */}

          <polyline
            points={points
              .map(
                (
                  point,
                  index,
                ) =>
                  `${xForIndex(
                    index,
                  )},${yForValue(
                    point.lower_95_w,
                  )}`,
              )
              .join(" ")}
            fill="none"
            stroke="currentColor"
            strokeOpacity={0.20}
            strokeWidth={1}
          />


          {/* Upper uncertainty */}

          <polyline
            points={points
              .map(
                (
                  point,
                  index,
                ) =>
                  `${xForIndex(
                    index,
                  )},${yForValue(
                    point.upper_95_w,
                  )}`,
              )
              .join(" ")}
            fill="none"
            stroke="currentColor"
            strokeOpacity={0.20}
            strokeWidth={1}
          />


          {/* Main prediction */}

          <polyline
            points={predictedPath}
            fill="none"
            stroke="currentColor"
            strokeWidth={3}
            strokeLinecap="round"
            strokeLinejoin="round"
          />


          {/* Peak marker */}

          <circle
            cx={xForIndex(
              maxIndex,
            )}
            cy={yForValue(
              points[maxIndex]
                .predicted_w,
            )}
            r={4}
            fill="currentColor"
          />


          {/* Start / middle / end labels */}

          <text
            x={padding.left}
            y={
              height - 10
            }
            fontSize={10}
            fill="currentColor"
            opacity={0.55}
          >
            {firstTime}
          </text>


          <text
            x={
              width / 2
            }
            y={
              height - 10
            }
            textAnchor="middle"
            fontSize={10}
            fill="currentColor"
            opacity={0.55}
          >
            {middleTime}
          </text>


          <text
            x={
              width -
              padding.right
            }
            y={
              height - 10
            }
            textAnchor="end"
            fontSize={10}
            fill="currentColor"
            opacity={0.55}
          >
            {lastTime}
          </text>

        </svg>

      </div>


      {/* =====================================================
          LEGEND
          ===================================================== */}

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          marginTop: 8,
          fontSize: 10,
          color:
            "var(--color-text-muted)",
        }}
      >

        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 5,
          }}
        >
          <span
            style={{
              width: 18,
              height: 3,
              borderRadius: 2,
              background:
                "currentColor",
            }}
          />
          Prediction
        </span>


        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 5,
          }}
        >
          <span
            style={{
              width: 18,
              height: 9,
              borderRadius: 3,
              background:
                "currentColor",
              opacity: 0.10,
            }}
          />
          Ensemble uncertainty
        </span>

      </div>


      {/* =====================================================
          PROVENANCE
          ===================================================== */}

      <p
        style={{
          fontSize: 10,
          lineHeight: 1.5,
          color:
            "var(--color-text-faint)",
          margin:
            "9px 0 0",
        }}
      >
        {state.forecast?.data_provenance_note}
      </p>

    </div>
  );
}


/**
 * Renders AI model replay data separately from live telemetry.
 */
export function ForecastPanel({
  title,
  state,
}: ForecastPanelProps) {

  return (
    <Card>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent:
            "space-between",
          marginBottom: 12,
        }}
      >

        <h3
          style={{
            fontSize: 14,
            margin: 0,
          }}
        >
          {title}
        </h3>

        <Badge tone="accent">
          AI MODEL REPLAY
        </Badge>

      </div>


      {state.status === "loading" && (
        <LoadingState
          message="Loading AI model replay..."
        />
      )}


      {state.status === "unavailable" && (
        <EmptyState
          title="AI replay unavailable"
          description="No prepared model replay data is currently available."
        />
      )}


      {state.status === "error" && (
        <ErrorState
          title="AI replay unavailable"
          description={
            state.errorMessage ??
            "Failed to load AI model replay."
          }
        />
      )}


      {state.status === "success" &&
        state.forecast && (
          <ForecastChart
            state={state}
          />
        )}

    </Card>
  );
}