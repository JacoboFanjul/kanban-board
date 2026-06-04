import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { LoginForm } from "@/components/LoginForm";

vi.mock("@/lib/api", () => ({
  ApiError: class ApiError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.status = status;
    }
  },
  apiLogin: vi.fn(),
  apiRegister: vi.fn(),
}));

import { apiLogin, apiRegister } from "@/lib/api";

describe("LoginForm", () => {
  it("renders username and password fields", () => {
    render(<LoginForm onLogin={vi.fn()} />);
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });

  it("calls onLogin with token on successful submit", async () => {
    vi.mocked(apiLogin).mockResolvedValueOnce("test-token");
    const onLogin = vi.fn();
    render(<LoginForm onLogin={onLogin} />);
    await userEvent.type(screen.getByLabelText(/username/i), "user");
    await userEvent.type(screen.getByLabelText(/^password/i), "password");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    expect(onLogin).toHaveBeenCalledWith("test-token");
  });

  it("shows error on failed login", async () => {
    vi.mocked(apiLogin).mockRejectedValueOnce(new Error("Invalid credentials"));
    render(<LoginForm onLogin={vi.fn()} />);
    await userEvent.type(screen.getByLabelText(/username/i), "user");
    await userEvent.type(screen.getByLabelText(/^password/i), "wrong");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/invalid/i);
  });

  it("switches to registration mode when 'Create one' is clicked", async () => {
    render(<LoginForm onLogin={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: /create one/i }));
    expect(screen.getByRole("button", { name: /create account/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
  });

  it("registers and calls onLogin with token on successful registration", async () => {
    vi.mocked(apiRegister).mockResolvedValueOnce("reg-token");
    const onLogin = vi.fn();
    render(<LoginForm onLogin={onLogin} />);
    await userEvent.click(screen.getByRole("button", { name: /create one/i }));
    await userEvent.type(screen.getByLabelText(/username/i), "newuser");
    await userEvent.type(screen.getByLabelText(/^password/i), "securepass");
    await userEvent.type(screen.getByLabelText(/confirm password/i), "securepass");
    await userEvent.click(screen.getByRole("button", { name: /create account/i }));
    expect(onLogin).toHaveBeenCalledWith("reg-token");
  });

  it("shows error when passwords do not match during registration", async () => {
    render(<LoginForm onLogin={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: /create one/i }));
    await userEvent.type(screen.getByLabelText(/username/i), "newuser");
    await userEvent.type(screen.getByLabelText(/^password/i), "securepass1");
    await userEvent.type(screen.getByLabelText(/confirm password/i), "securepass2");
    await userEvent.click(screen.getByRole("button", { name: /create account/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/do not match/i);
  });
});
