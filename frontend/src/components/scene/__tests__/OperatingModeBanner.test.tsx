import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { OperatingModeBanner } from "@/components/scene/OperatingModeBanner";

describe("OperatingModeBanner", () => {
  it("shows an unknown state when no mode is available yet", () => {
    render(<OperatingModeBanner mode={null} reason={null} />);
    expect(screen.getByText(/OPERATING MODE: UNKNOWN/)).toBeInTheDocument();
  });

  it("renders NORMAL_MODE with its reason", () => {
    render(<OperatingModeBanner mode="NORMAL_MODE" reason="Everything is fine." />);
    expect(screen.getByText("NORMAL_MODE")).toBeInTheDocument();
    expect(screen.getByText("Everything is fine.")).toBeInTheDocument();
    expect(screen.getByText("RECOMMENDED")).toBeInTheDocument();
  });

  it("renders ECO_MODE with its reason", () => {
    render(<OperatingModeBanner mode="ECO_MODE" reason="Deferring a load." />);
    expect(screen.getByText("ECO_MODE")).toBeInTheDocument();
  });

  it("renders EMERGENCY_MODE with its reason", () => {
    render(<OperatingModeBanner mode="EMERGENCY_MODE" reason="SOC critically low." />);
    expect(screen.getByText("EMERGENCY_MODE")).toBeInTheDocument();
    expect(screen.getByText("SOC critically low.")).toBeInTheDocument();
  });

  it("always labels the mode as RECOMMENDED, never implying an actual mode switch occurred", () => {
    render(<OperatingModeBanner mode="EMERGENCY_MODE" reason="x" />);
    expect(screen.getByText("RECOMMENDED")).toBeInTheDocument();
  });
});
