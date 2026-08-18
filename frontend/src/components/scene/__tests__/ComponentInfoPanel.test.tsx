import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ComponentInfoPanel } from "@/components/scene/ComponentInfoPanel";
import type { SelectedComponent } from "@/components/scene/selection";

describe("ComponentInfoPanel", () => {
  it("shows an empty state when nothing is selected", () => {
    render(<ComponentInfoPanel selected={null} />);
    expect(screen.getByText("Nothing selected")).toBeInTheDocument();
  });

  it("renders the selected component's title, kind badge, and details", () => {
    const selected: SelectedComponent = {
      kind: "battery",
      title: "Battery Storage",
      details: [
        { label: "State of charge", value: "62 %" },
        { label: "Power flow", value: "Charging" },
      ],
    };
    render(<ComponentInfoPanel selected={selected} />);
    expect(screen.getByText("Battery Storage")).toBeInTheDocument();
    expect(screen.getByText("battery")).toBeInTheDocument();
    expect(screen.getByText("62 %")).toBeInTheDocument();
    expect(screen.getByText("Charging")).toBeInTheDocument();
  });
});
