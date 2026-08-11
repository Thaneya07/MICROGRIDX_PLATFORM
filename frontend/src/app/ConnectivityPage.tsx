import { Badge, Card, MetricCard, PageHeader, StatusIndicator } from "@/components/ui";
import { Button } from "@/components/ui";
import { LoadingState, ErrorState } from "@/components/ui";
import { useBackendConnectivity } from "@/hooks/useBackendConnectivity";
import "./ConnectivityPage.css";

/**
 * Demonstrates that the React frontend can reach the FastAPI backend and
 * that the backend can reach PostgreSQL. This is a foundation/verification
 * page for Phase 1 — not a product dashboard, and it renders no telemetry
 * or energy data of any kind.
 */
export function ConnectivityPage() {
  const { status, api, database, errorMessage, checkedAt, refresh } = useBackendConnectivity();

  return (
    <div className="mgx-page">
      <PageHeader
        eyebrow="Phase 1 · Foundation"
        title="System connectivity"
        description="Confirms the frontend can reach the FastAPI backend, and the backend can reach PostgreSQL. No energy data is shown here — that arrives in a later phase."
        actions={
          <Button variant="secondary" size="sm" onClick={refresh} disabled={status === "loading"}>
            Re-check
          </Button>
        }
      />

      {status === "loading" && <LoadingState message="Checking backend and database connectivity..." />}

      {status === "error" && (
        <ErrorState
          title="Could not reach the backend"
          description={errorMessage ?? "The API did not respond as expected."}
          onRetry={refresh}
        />
      )}

      {status === "success" && (
        <div className="mgx-connectivity-grid">
          <Card>
            <div className="mgx-connectivity-card-header">
              <h3>API service</h3>
              <StatusIndicator status="online" label="Reachable" />
            </div>
            <dl className="mgx-connectivity-details">
              <div>
                <dt>Service</dt>
                <dd className="mono">{api?.service}</dd>
              </div>
              <div>
                <dt>Status</dt>
                <dd>
                  <Badge tone="online">{api?.status}</Badge>
                </dd>
              </div>
            </dl>
          </Card>

          <Card>
            <div className="mgx-connectivity-card-header">
              <h3>Database</h3>
              <StatusIndicator status="online" label="Connected" />
            </div>
            <dl className="mgx-connectivity-details">
              <div>
                <dt>Backend reports</dt>
                <dd className="mono">{database?.database}</dd>
              </div>
              <div>
                <dt>Status</dt>
                <dd>
                  <Badge tone="online">{database?.status}</Badge>
                </dd>
              </div>
            </dl>
          </Card>

          <MetricCard label="Last checked" value={checkedAt ? checkedAt.toLocaleTimeString() : "—"} />
        </div>
      )}
    </div>
  );
}
