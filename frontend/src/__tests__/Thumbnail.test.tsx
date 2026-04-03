import { describe, it, expect, vi } from "vitest";
import { render, fireEvent } from "@testing-library/react";
import Thumbnail from "../components/Thumbnail";

vi.mock("../services/api", () => ({
  getThumbnailUrl: (assetId: string, size = "thumbnail") =>
    `/api/thumbnails/${assetId}?size=${size}`,
}));

describe("Thumbnail", () => {
  it("renders an img element with the correct src", () => {
    render(<Thumbnail assetId="asset-123" />);
    const img = document.querySelector("img");
    expect(img).not.toBeNull();
    expect(img!.src).toContain("/api/thumbnails/asset-123");
  });

  it("shows a fallback placeholder on image load error", () => {
    render(<Thumbnail assetId="bad-id" />);
    const img = document.querySelector("img")!;
    fireEvent.error(img);
    // After error, the img should be gone (replaced by placeholder div)
    expect(document.querySelector("img")).toBeNull();
  });

  it("uses the provided size prop", () => {
    const { container } = render(<Thumbnail assetId="asset-456" size={120} />);
    // The outer-most rendered div carries the size styles
    const wrapper = container.firstElementChild as HTMLDivElement;
    expect(wrapper.style.width).toBe("120px");
    expect(wrapper.style.height).toBe("120px");
  });

  it("fires onClick when the wrapper is clicked", () => {
    const onClick = vi.fn();
    const { container } = render(<Thumbnail assetId="a" onClick={onClick} />);
    const wrapper = container.querySelector("div")!;
    fireEvent.click(wrapper);
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("renders with pointer cursor when onClick is provided", () => {
    const { container } = render(<Thumbnail assetId="a" onClick={() => {}} />);
    const wrapper = container.querySelector("div") as HTMLDivElement;
    expect(wrapper.style.cursor).toBe("pointer");
  });

  it("renders with default cursor when no onClick", () => {
    const { container } = render(<Thumbnail assetId="a" />);
    const wrapper = container.querySelector("div") as HTMLDivElement;
    expect(wrapper.style.cursor).toBe("default");
  });
});
