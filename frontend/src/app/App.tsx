import { useState } from "react";
import { ConnectivityPage } from "./ConnectivityPage";
import { VisualizationPage } from "./VisualizationPage";
import { Button } from "@/components/ui";

type Tab = "connectivity" | "visualization";

export function App() {
  const [tab, setTab] = useState<Tab>("connectivity");

  return (
    <div>
      <div style={{ display: "flex", gap: 8, padding: "16px 24px 0", justifyContent: "center" }}>
        <Button variant={tab === "connectivity" ? "primary" : "ghost"} size="sm" onClick={() => setTab("connectivity")}>
          System connectivity
        </Button>
        <Button variant={tab === "visualization" ? "primary" : "ghost"} size="sm" onClick={() => setTab("visualization")}>
          3D Visualization
        </Button>
      </div>
      {tab === "connectivity" ? <ConnectivityPage /> : <VisualizationPage />}
    </div>
  );
}

