import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import Assets from "../pages/Assets";

vi.mock("../services/api", () => ({
  getAssets: vi.fn(),
  getAssetCount: vi.fn(),
  getThumbnailUrl: (assetId: string, size = "thumbnail") =>
    `/api/thumbnails/${assetId}?size=${size}`,
}));

import { getAssets, getAssetCount } from "../services/api";

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/assets"]}>
        <Assets />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("Assets page", () => {
  beforeEach(() => {
    vi.mocked(getAssets).mockResolvedValue([
      {
        id: "asset-1",
        immich_id: "immich-1",
        original_filename: "photo.jpg",
        file_created_at: "2026-05-05T10:00:00Z",
        asset_type: "IMAGE",
        is_favorite: false,
        is_archived: false,
        is_external_library: false,
        created_at: "2026-05-05T10:00:00Z",
      },
    ]);
    vi.mocked(getAssetCount).mockResolvedValue({ count: 1 });
  });

  it("lazy-loads and asynchronously decodes grid thumbnails", async () => {
    renderPage();

    const image = await screen.findByRole("img", { name: "photo.jpg" });
    expect(image).toHaveAttribute("loading", "lazy");
    expect(image).toHaveAttribute("decoding", "async");
  });
});
