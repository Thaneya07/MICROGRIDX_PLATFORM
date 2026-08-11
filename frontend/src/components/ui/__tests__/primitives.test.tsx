import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { StatusIndicator } from "@/components/ui/StatusIndicator";

describe("Button", () => {
  it("renders children and responds to click", () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Save changes</Button>);
    const button = screen.getByRole("button", { name: "Save changes" });
    button.click();
    expect(handleClick).toHaveBeenCalledOnce();
  });
});

describe("Badge", () => {
  it("renders provided content", () => {
    render(<Badge tone="online">connected</Badge>);
    expect(screen.getByText("connected")).toBeInTheDocument();
  });
});

describe("StatusIndicator", () => {
  it("falls back to a default label per status", () => {
    render(<StatusIndicator status="offline" />);
    expect(screen.getByText("Offline")).toBeInTheDocument();
  });
});
