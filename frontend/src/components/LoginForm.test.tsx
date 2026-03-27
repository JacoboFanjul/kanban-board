import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { LoginForm } from "@/components/LoginForm";

vi.mock("@/lib/api", () => ({
  apiLogin: vi.fn(),
}));

import { apiLogin } from "@/lib/api";

describe("LoginForm", () => {
  it("renders username and password fields", () => {
    render(<LoginForm onLogin={vi.fn()} />);
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });

  it("calls onLogin with token on successful submit", async () => {
    vi.mocked(apiLogin).mockResolvedValueOnce("test-token");
    const onLogin = vi.fn();
    render(<LoginForm onLogin={onLogin} />);
    await userEvent.type(screen.getByLabelText(/username/i), "user");
    await userEvent.type(screen.getByLabelText(/password/i), "password");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    expect(onLogin).toHaveBeenCalledWith("test-token");
  });

  it("shows error on failed login", async () => {
    vi.mocked(apiLogin).mockRejectedValueOnce(new Error("Invalid credentials"));
    render(<LoginForm onLogin={vi.fn()} />);
    await userEvent.type(screen.getByLabelText(/username/i), "user");
    await userEvent.type(screen.getByLabelText(/password/i), "wrong");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/invalid/i);
  });
});
