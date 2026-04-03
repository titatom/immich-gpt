import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ConfidenceBadge from "../components/ConfidenceBadge";

describe("ConfidenceBadge", () => {
  it("renders nothing when confidence is undefined", () => {
    const { container } = render(<ConfidenceBadge />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders the percentage rounded to nearest integer", () => {
    render(<ConfidenceBadge confidence={0.856} />);
    expect(screen.getByText("86%")).toBeInTheDocument();
  });

  it("renders 0% for zero confidence", () => {
    render(<ConfidenceBadge confidence={0} />);
    expect(screen.getByText("0%")).toBeInTheDocument();
  });

  it("renders 100% for full confidence", () => {
    render(<ConfidenceBadge confidence={1} />);
    expect(screen.getByText("100%")).toBeInTheDocument();
  });

  it("uses green color for >= 80% confidence", () => {
    const { container } = render(<ConfidenceBadge confidence={0.8} />);
    const span = container.querySelector("span")!;
    expect(span.style.color).toBe("rgb(34, 197, 94)");
  });

  it("uses amber color for 60-79% confidence", () => {
    const { container } = render(<ConfidenceBadge confidence={0.65} />);
    const span = container.querySelector("span")!;
    expect(span.style.color).toBe("rgb(245, 158, 11)");
  });

  it("uses red color for < 60% confidence", () => {
    const { container } = render(<ConfidenceBadge confidence={0.4} />);
    const span = container.querySelector("span")!;
    expect(span.style.color).toBe("rgb(239, 68, 68)");
  });
});
