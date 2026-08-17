import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DataSourceBadge } from "@/components/scene/DataSourceBadge";

describe("DataSourceBadge", () => {
  it("clearly labels SIMULATED data as not physical", () => {
    render(<DataSourceBadge source="SIMULATED" />);
    expect(screen.getByText(/SIMULATED/)).toBeInTheDocument();
    expect(screen.getByText(/not physical sensor data/)).toBeInTheDocument();
  });

  it("clearly labels HARDWARE data as live sensor data", () => {
    render(<DataSourceBadge source="HARDWARE" />);
    expect(screen.getByText(/HARDWARE/)).toBeInTheDocument();
    expect(screen.getByText(/live sensor data/)).toBeInTheDocument();
  });

  it("shows an explicit no-data state rather than guessing", () => {
    render(<DataSourceBadge source={null} />);
    expect(screen.getByText("NO DATA")).toBeInTheDocument();
  });
});
