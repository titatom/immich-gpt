import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import AdminUsers from "../pages/AdminUsers";

vi.mock("../services/api", () => ({
  adminListUsers: vi.fn(),
  adminCreateUser: vi.fn(),
  adminUpdateUser: vi.fn(),
  adminResetPassword: vi.fn(),
  adminDeleteUser: vi.fn(),
}));

import { adminListUsers, adminResetPassword } from "../services/api";

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  return render(
    <QueryClientProvider client={client}>
      <AdminUsers />
    </QueryClientProvider>
  );
}

describe("AdminUsers", () => {
  beforeEach(() => {
    vi.mocked(adminListUsers).mockResolvedValue([
      {
        id: "user-1",
        email: "user@example.com",
        username: "user",
        role: "user",
        is_active: true,
        force_password_change: false,
        created_at: "2026-05-05T10:00:00Z",
      },
    ]);
    vi.mocked(adminResetPassword).mockResolvedValue({
      token: "sensitive-reset-token",
    });

    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
  });

  it("copies reset tokens without rendering the secret", async () => {
    renderPage();

    await userEvent.click(await screen.findByTitle("Reset password"));

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith("sensitive-reset-token");
    });
    expect(screen.getByText(/copied to your clipboard/i)).toBeInTheDocument();
    expect(screen.queryByText("sensitive-reset-token")).not.toBeInTheDocument();
  });
});
