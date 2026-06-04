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
  apiListBoards: vi.fn(),
  apiGetBoard: vi.fn(),
  apiCreateBoard: vi.fn(),
  apiRenameBoard: vi.fn(),
  apiDeleteBoard: vi.fn(),
  apiRenameColumn: vi.fn(),
  apiCreateColumn: vi.fn(),
  apiDeleteColumn: vi.fn(),
  apiMoveColumn: vi.fn(),
  apiSetWipLimit: vi.fn(),
  apiCreateCard: vi.fn(),
  apiUpdateCard: vi.fn(),
  apiArchiveCard: vi.fn(),
  apiUnarchiveCard: vi.fn(),
  apiGetArchivedCards: vi.fn(),
  apiSearchCards: vi.fn(),
  apiDeleteCard: vi.fn(),
  apiMoveCard: vi.fn(),
  apiChangePassword: vi.fn(),
}));

import {
  apiListBoards,
  apiGetBoard,
  apiRenameColumn,
  apiCreateCard,
  apiDeleteCard,
  apiUpdateCard,
  apiArchiveCard,
  apiGetArchivedCards,
  apiSearchCards,
} from "@/lib/api";

const mockBoardSummaries = [
  { id: "board-1", title: "My Board", created_at: "2026-01-01T00:00:00Z" },
];

const mockBoard = {
  id: "board-1",
  title: "My Board",
  columns: [
    {
      id: "col-backlog",
      title: "Backlog",
      wip_limit: null,
      cards: [
        { id: "card-1", title: "Card One", details: "Details", due_date: null, label: null, priority: null, created_at: null },
      ],
    },
    { id: "col-discovery", title: "Discovery", wip_limit: null, cards: [] },
    { id: "col-progress", title: "In Progress", wip_limit: null, cards: [] },
    { id: "col-review", title: "Review", wip_limit: null, cards: [] },
    { id: "col-done", title: "Done", wip_limit: null, cards: [] },
  ],
};

beforeEach(() => {
  vi.mocked(apiListBoards).mockResolvedValue(mockBoardSummaries);
  vi.mocked(apiGetBoard).mockResolvedValue(mockBoard);
  vi.mocked(apiRenameColumn).mockResolvedValue(undefined);
  vi.mocked(apiCreateCard).mockResolvedValue({
    id: "card-new",
    title: "New card",
    details: "Notes",
    due_date: null,
    label: null,
    priority: null,
    created_at: "2026-01-01T00:00:00Z",
  });
  vi.mocked(apiUpdateCard).mockResolvedValue(undefined);
  vi.mocked(apiDeleteCard).mockResolvedValue(undefined);
  vi.mocked(apiArchiveCard).mockResolvedValue(undefined);
  vi.mocked(apiGetArchivedCards).mockResolvedValue([]);
  vi.mocked(apiSearchCards).mockResolvedValue([]);
});

const renderBoard = () =>
  render(<KanbanBoard token="test-token" username="user" />);

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

  it("archives a card optimistically and calls API", async () => {
    renderBoard();
    const column = (await screen.findAllByTestId(/column-/i))[0];
    await screen.findByText("Card One");
    await userEvent.click(
      within(column).getByRole("button", { name: /archive card one/i }),
    );
    expect(within(column).queryByText("Card One")).not.toBeInTheDocument();
    await waitFor(() => {
      expect(vi.mocked(apiArchiveCard)).toHaveBeenCalledWith("test-token", "card-1");
    });
  });

  it("shows search results when typing in the search bar", async () => {
    vi.mocked(apiSearchCards).mockResolvedValue([
      {
        id: "card-1",
        title: "Card One",
        details: "Details",
        due_date: null,
        label: null,
        priority: null,
        created_at: null,
        column_id: "col-backlog",
        column_title: "Backlog",
      },
    ]);
    renderBoard();
    await screen.findAllByTestId(/column-/i);
    await userEvent.type(screen.getByPlaceholderText(/search cards/i), "card");
    await waitFor(() => {
      expect(vi.mocked(apiSearchCards)).toHaveBeenCalledWith("test-token", "board-1", { q: "card" });
    });
  });

  it("enters card edit mode and saves via API", async () => {
    renderBoard();
    const column = (await screen.findAllByTestId(/column-/i))[0];
    await screen.findByText("Card One");
    await userEvent.click(
      within(column).getByRole("button", { name: /edit card one/i }),
    );
    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.clear(titleInput);
    await userEvent.type(titleInput, "Updated Title");
    await userEvent.click(within(column).getByRole("button", { name: /save/i }));
    await waitFor(() => {
      expect(vi.mocked(apiUpdateCard)).toHaveBeenCalledWith(
        "test-token",
        "card-1",
        expect.objectContaining({ title: "Updated Title" }),
      );
    });
  });
});
