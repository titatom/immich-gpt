import { describe, it, expect, vi } from "vitest";

vi.mock("axios", async () => {
  const mockGet = vi.fn();
  const mockPost = vi.fn();
  const mockDelete = vi.fn();
  const mockPatch = vi.fn();
  const instance = { get: mockGet, post: mockPost, delete: mockDelete, patch: mockPatch };
  return {
    default: {
      create: vi.fn(() => instance),
      ...instance,
    },
  };
});

// Import after mock is set up
const apiModule = await import("../services/api");

describe("api service", () => {
  it("getThumbnailUrl returns expected path", () => {
    const url = apiModule.getThumbnailUrl("asset-1");
    expect(url).toBe("/api/thumbnails/asset-1?size=thumbnail");
  });

  it("getThumbnailUrl accepts custom size", () => {
    const url = apiModule.getThumbnailUrl("asset-2", "preview");
    expect(url).toBe("/api/thumbnails/asset-2?size=preview");
  });
});
