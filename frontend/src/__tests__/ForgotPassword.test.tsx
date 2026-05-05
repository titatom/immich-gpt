import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import ForgotPassword from "../pages/ForgotPassword";
import { forgotPassword } from "../services/api";

vi.mock("../components/BrandLogo", () => ({
  default: () => <div>Immich GPT</div>,
}));

vi.mock("../services/api", () => ({
  forgotPassword: vi.fn(),
}));

describe("ForgotPassword page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
  });

  it("copies generated reset tokens without rendering them", async () => {
    vi.mocked(forgotPassword).mockResolvedValue({
      message: "Reset token generated",
      token: "forgot-secret-token",
    });

    render(<ForgotPassword />);

    await userEvent.type(screen.getByLabelText("Email"), "admin@example.com");
    await userEvent.click(screen.getByRole("button", { name: /generate reset token/i }));

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith("forgot-secret-token");
    });
    expect(screen.queryByText("forgot-secret-token")).not.toBeInTheDocument();
    expect(screen.getByText(/copied to your clipboard/i)).toBeInTheDocument();
  });
});
