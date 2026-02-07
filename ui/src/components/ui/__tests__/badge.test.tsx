import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge } from "../badge";

describe("Badge", () => {
  it("renders with default variant", () => {
    render(<Badge>Default Badge</Badge>);
    const badge = screen.getByText("Default Badge");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass("bg-primary", "text-primary-foreground");
  });

  it("renders with different variants", () => {
    const { rerender } = render(<Badge variant="default">Default</Badge>);
    let badge = screen.getByText("Default");
    expect(badge).toHaveClass("bg-primary");

    rerender(<Badge variant="secondary">Secondary</Badge>);
    badge = screen.getByText("Secondary");
    expect(badge).toHaveClass("bg-secondary");

    rerender(<Badge variant="destructive">Destructive</Badge>);
    badge = screen.getByText("Destructive");
    expect(badge).toHaveClass("bg-destructive");

    rerender(<Badge variant="success">Success</Badge>);
    badge = screen.getByText("Success");
    expect(badge).toHaveClass("bg-success/15", "text-success");

    rerender(<Badge variant="warning">Warning</Badge>);
    badge = screen.getByText("Warning");
    expect(badge).toHaveClass("bg-warning/15", "text-warning");

    rerender(<Badge variant="info">Info</Badge>);
    badge = screen.getByText("Info");
    expect(badge).toHaveClass("bg-info/15", "text-info");

    rerender(<Badge variant="outline">Outline</Badge>);
    badge = screen.getByText("Outline");
    expect(badge).toHaveClass("text-foreground");
  });

  it("applies custom className", () => {
    render(<Badge className="custom-badge-class">Badge</Badge>);
    const badge = screen.getByText("Badge");
    expect(badge).toHaveClass("custom-badge-class");
    expect(badge).toHaveClass("inline-flex", "items-center", "rounded-full");
  });

  it("renders children correctly", () => {
    render(
      <Badge>
        <span>Nested content</span>
      </Badge>,
    );
    expect(screen.getByText("Nested content")).toBeInTheDocument();
  });

  it("applies common badge classes", () => {
    render(<Badge>Test</Badge>);
    const badge = screen.getByText("Test");
    expect(badge).toHaveClass(
      "inline-flex",
      "items-center",
      "rounded-full",
      "border",
      "px-2.5",
      "py-0.5",
      "text-xs",
      "font-semibold",
    );
  });
});
