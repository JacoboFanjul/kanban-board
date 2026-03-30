import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { KanbanBoard } from "@/components/KanbanBoard";

vi.mock("@/lib/api", () => ({
  ApiError: class ApiError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.status = status;
    }
  },
  apiGetBoard: vi.fn(),
  apiRenameColumn: vi.fn(),
  apiCreateCard: vi.fn(),
  apiDeleteCard: vi.fn(),
  apiMoveCard: vi.fn(),
}));

import {
  apiGetBoard,
  apiRenameColumn,
  apiCreateCard,
  apiDeleteCard,
} from "@/lib/api";

const mockBoard = {
  columns: [
    {
      id: "col-backlog",
      title: "Backlog",
      cards: [{ id: "card-1", title: "Card One", details: "Details" }],
    },
    { id: "col-discovery", title: "Discovery", cards: [] },
    { id: "col-progress", title: "In Progress", cards: [] },
    { id: "col-review", title: "Review", cards: [] },
    { id: "col-done", title: "Done", cards: [] },
  ],
};

beforeEach(() => {
  vi.mocked(apiGetBoard).mockResolvedValue(mockBoard);
  vi.mocked(apiRenameColumn).mockResolvedValue(undefined);
  vi.mocked(apiCreateCard).mockResolvedValue({
    id: "card-new",
    title: "New card",
    details: "Notes",
  });
  vi.mocked(apiDeleteCard).mockResolvedValue(undefined);
});

const renderBoard = () => render(<KanbanBoard token="test-token" />);

describe("KanbanBoard", () => {
  it("renders five columns after loading", async () => {
    renderBoard();
    const columns = await screen.findAllByTestId(/column-/i);
    expect(columns).toHaveLength(5);
  });

  it("renames a column and commits to API on blur", async () => {
    renderBoard();
    const column = (await screen.findAllByTestId(/column-/i))[0];
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");
    expect(input).toHaveValue("New Name");
    await userEvent.tab();
    await waitFor(() => {
      expect(vi.mocked(apiRenameColumn)).toHaveBeenCalledWith(
        "test-token",
        "col-backlog",
        "New Name",
      );
    });
  });

  it("adds a card via API and renders it", async () => {
    renderBoard();
    const column = (await screen.findAllByTestId(/column-/i))[0];
    await userEvent.click(within(column).getByRole("button", { name: /add a card/i }));
    await userEvent.type(within(column).getByPlaceholderText(/card title/i), "New card");
    await userEvent.type(within(column).getByPlaceholderText(/details/i), "Notes");
    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    await waitFor(() => {
      expect(vi.mocked(apiCreateCard)).toHaveBeenCalledWith(
        "test-token",
        "col-backlog",
        "New card",
        "Notes",
      );
    });
    expect(await within(column).findByText("New card")).toBeInTheDocument();
  });

  it("deletes a card optimistically and calls API", async () => {
    renderBoard();
    const column = (await screen.findAllByTestId(/column-/i))[0];
    await screen.findByText("Card One");
    await userEvent.click(
      within(column).getByRole("button", { name: /delete card one/i }),
    );
    expect(within(column).queryByText("Card One")).not.toBeInTheDocument();
    await waitFor(() => {
      expect(vi.mocked(apiDeleteCard)).toHaveBeenCalledWith("test-token", "card-1");
    });
  });
});

