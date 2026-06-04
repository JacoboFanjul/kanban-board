"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { moveCard, type BoardData } from "@/lib/kanban";
import {
  ApiError,
  apiGetBoard,
  apiListBoards,
  apiCreateBoard,
  apiRenameBoard,
  apiDeleteBoard,
  apiRenameColumn,
  apiCreateColumn,
  apiDeleteColumn,
  apiSetWipLimit,
  apiCreateCard,
  apiUpdateCard,
  apiArchiveCard,
  apiGetArchivedCards,
  apiSearchCards,
  apiDeleteCard,
  apiMoveCard,
  apiChangePassword,
  type ApiBoard,
  type ApiBoardSummary,
  type ApiCardSearchResult,
} from "@/lib/api";

interface Props {
  token: string;
  username: string;
  onLogout?: () => void;
}

function normalizeBoard(api: ApiBoard): BoardData {
  const cards: BoardData["cards"] = {};
  const columns = api.columns.map((col) => {
    col.cards.forEach((card) => {
      cards[card.id] = card;
    });
    return {
      id: col.id,
      title: col.title,
      wip_limit: col.wip_limit,
      cardIds: col.cards.map((c) => c.id),
    };
  });
  return { columns, cards };
}

export const KanbanBoard = ({ token, username, onLogout }: Props) => {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [boardSummaries, setBoardSummaries] = useState<ApiBoardSummary[]>([]);
  const [activeBoardId, setActiveBoardId] = useState<string | null>(null);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [showBoardMenu, setShowBoardMenu] = useState(false);
  const [newBoardTitle, setNewBoardTitle] = useState("");
  const [showNewBoardForm, setShowNewBoardForm] = useState(false);
  const [showPasswordForm, setShowPasswordForm] = useState(false);
  const [passwordForm, setPasswordForm] = useState({ current: "", next: "", confirm: "" });
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordSuccess, setPasswordSuccess] = useState(false);
  const [boardTitle, setBoardTitle] = useState("");
  const [editingBoardTitle, setEditingBoardTitle] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<ApiCardSearchResult[] | null>(null);
  const [showArchive, setShowArchive] = useState(false);
  const [archivedCards, setArchivedCards] = useState<ApiCardSearchResult[]>([]);
  const [wipEditingColId, setWipEditingColId] = useState<string | null>(null);
  const [wipInputValue, setWipInputValue] = useState("");
  const boardMenuRef = useRef<HTMLDivElement>(null);

  const handle401 = useCallback(() => {
    onLogout?.();
  }, [onLogout]);

  const loadBoard = useCallback(
    (boardId: string) => {
      setLoadError(false);
      apiGetBoard(token, boardId)
        .then((data) => {
          setBoard(normalizeBoard(data));
          setBoardTitle(data.title);
        })
        .catch((err: unknown) => {
          if (err instanceof ApiError && err.status === 401) handle401();
          else setLoadError(true);
        });
    },
    [token, handle401],
  );

  const refreshBoards = useCallback(async () => {
    try {
      const summaries = await apiListBoards(token);
      setBoardSummaries(summaries);
      return summaries;
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) handle401();
      return [];
    }
  }, [token, handle401]);

  useEffect(() => {
    apiListBoards(token)
      .then((summaries) => {
        setBoardSummaries(summaries);
        if (summaries.length > 0) {
          const first = summaries[0];
          setActiveBoardId(first.id);
          loadBoard(first.id);
        } else {
          setBoard({ columns: [], cards: {} });
        }
      })
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 401) handle401();
      });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Close board menu on outside click
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (boardMenuRef.current && !boardMenuRef.current.contains(e.target as Node)) {
        setShowBoardMenu(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
  );

  const cardsById = useMemo(() => board?.cards ?? {}, [board?.cards]);

  const handleDragStart = (event: DragStartEvent) => {
    setActiveCardId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);
    if (!over || active.id === over.id || !board) return;

    const activeId = active.id as string;
    const prevBoard = board;
    const newColumns = moveCard(board.columns, activeId, over.id as string);
    setBoard((prev) => (prev ? { ...prev, columns: newColumns } : prev));

    const targetColumn = newColumns.find((col) => col.cardIds.includes(activeId));
    if (targetColumn) {
      const position = targetColumn.cardIds.indexOf(activeId);
      apiMoveCard(token, activeId, targetColumn.id, position).catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 401) handle401();
        else setBoard(prevBoard);
      });
    }
  };

  const handleRenameColumn = (columnId: string, title: string) => {
    setBoard((prev) =>
      prev
        ? { ...prev, columns: prev.columns.map((c) => (c.id === columnId ? { ...c, title } : c)) }
        : prev,
    );
  };

  const handleRenameColumnCommit = (columnId: string, title: string) => {
    apiRenameColumn(token, columnId, title).catch((err: unknown) => {
      if (err instanceof ApiError && err.status === 401) handle401();
      else if (activeBoardId) loadBoard(activeBoardId);
    });
  };

  const handleAddCard = async (columnId: string, title: string, details: string) => {
    try {
      const card = await apiCreateCard(token, columnId, title, details);
      setBoard((prev) =>
        prev
          ? {
              ...prev,
              cards: { ...prev.cards, [card.id]: card },
              columns: prev.columns.map((col) =>
                col.id === columnId ? { ...col, cardIds: [...col.cardIds, card.id] } : col,
              ),
            }
          : prev,
      );
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) handle401();
    }
  };

  const handleEditCard = async (cardId: string, title: string, details: string) => {
    setBoard((prev) =>
      prev
        ? { ...prev, cards: { ...prev.cards, [cardId]: { ...prev.cards[cardId], title, details } } }
        : prev,
    );
    try {
      await apiUpdateCard(token, cardId, { title, details });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) handle401();
      else if (activeBoardId) loadBoard(activeBoardId);
    }
  };

  const handleDeleteCard = (columnId: string, cardId: string) => {
    const prevBoard = board;
    setBoard((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        cards: Object.fromEntries(Object.entries(prev.cards).filter(([id]) => id !== cardId)),
        columns: prev.columns.map((col) =>
          col.id === columnId
            ? { ...col, cardIds: col.cardIds.filter((id) => id !== cardId) }
            : col,
        ),
      };
    });
    apiDeleteCard(token, cardId).catch((err: unknown) => {
      if (err instanceof ApiError && err.status === 401) handle401();
      else setBoard(prevBoard);
    });
  };

  const handleArchiveCard = (columnId: string, cardId: string) => {
    const prevBoard = board;
    setBoard((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        cards: Object.fromEntries(Object.entries(prev.cards).filter(([id]) => id !== cardId)),
        columns: prev.columns.map((col) =>
          col.id === columnId
            ? { ...col, cardIds: col.cardIds.filter((id) => id !== cardId) }
            : col,
        ),
      };
    });
    apiArchiveCard(token, cardId).catch((err) => {
      if (err instanceof ApiError && err.status === 401) handle401();
      else setBoard(prevBoard);
    });
  };

  const handleSearch = async (q: string) => {
    setSearchQuery(q);
    if (!activeBoardId) return;
    if (!q.trim()) {
      setSearchResults(null);
      return;
    }
    try {
      const results = await apiSearchCards(token, activeBoardId, { q });
      setSearchResults(results);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) handle401();
    }
  };

  const handleShowArchive = async () => {
    if (!activeBoardId) return;
    try {
      const cards = await apiGetArchivedCards(token, activeBoardId);
      setArchivedCards(cards);
      setShowArchive(true);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) handle401();
    }
  };

  const handleUnarchive = async (cardId: string) => {
    try {
      const { apiUnarchiveCard } = await import("@/lib/api");
      await apiUnarchiveCard(token, cardId);
      setArchivedCards((prev) => prev.filter((c) => c.id !== cardId));
      if (activeBoardId) loadBoard(activeBoardId);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) handle401();
    }
  };

  const handleSetWipLimit = async (columnId: string, value: string) => {
    const num = value === "" ? null : parseInt(value, 10);
    if (value !== "" && (isNaN(num!) || num! < 1)) return;
    try {
      await apiSetWipLimit(token, columnId, num);
      setBoard((prev) =>
        prev
          ? { ...prev, columns: prev.columns.map((c) => c.id === columnId ? { ...c, wip_limit: num } : c) }
          : prev,
      );
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) handle401();
    }
    setWipEditingColId(null);
  };

  const handleAddColumn = async () => {
    if (!activeBoardId) return;
    try {
      const col = await apiCreateColumn(token, activeBoardId, "New Column");
      setBoard((prev) =>
        prev
          ? { ...prev, columns: [...prev.columns, { id: col.id, title: col.title, wip_limit: null, cardIds: [] }] }
          : prev,
      );
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) handle401();
    }
  };

  const handleDeleteColumn = (columnId: string) => {
    const prevBoard = board;
    setBoard((prev) =>
      prev
        ? {
            columns: prev.columns.filter((c) => c.id !== columnId),
            cards: Object.fromEntries(
              Object.entries(prev.cards).filter(
                ([id]) =>
                  !prevBoard?.columns.find((c) => c.id === columnId)?.cardIds.includes(id),
              ),
            ),
          }
        : prev,
    );
    apiDeleteColumn(token, columnId).catch((err) => {
      if (err instanceof ApiError && err.status === 401) handle401();
      else setBoard(prevBoard);
    });
  };

  const handleSwitchBoard = (boardId: string) => {
    setActiveBoardId(boardId);
    setBoard(null);
    loadBoard(boardId);
    setShowBoardMenu(false);
  };

  const handleCreateBoard = async () => {
    const title = newBoardTitle.trim();
    if (!title) return;
    try {
      const newBoard = await apiCreateBoard(token, title);
      await refreshBoards();
      setNewBoardTitle("");
      setShowNewBoardForm(false);
      setActiveBoardId(newBoard.id);
      loadBoard(newBoard.id);
      setShowBoardMenu(false);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) handle401();
    }
  };

  const handleDeleteBoard = async (boardId: string) => {
    if (!confirm("Delete this board and all its contents?")) return;
    try {
      await apiDeleteBoard(token, boardId);
      const remaining = boardSummaries.filter((b) => b.id !== boardId);
      await refreshBoards();
      setShowBoardMenu(false);
      if (activeBoardId === boardId) {
        if (remaining.length > 0) {
          setActiveBoardId(remaining[0].id);
          loadBoard(remaining[0].id);
        } else {
          setActiveBoardId(null);
          setBoard({ columns: [], cards: {} });
        }
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) handle401();
    }
  };

  const handleBoardTitleCommit = async () => {
    if (!activeBoardId || !boardTitle.trim()) return;
    setEditingBoardTitle(false);
    try {
      await apiRenameBoard(token, activeBoardId, boardTitle.trim());
      setBoardSummaries((prev) =>
        prev.map((b) => (b.id === activeBoardId ? { ...b, title: boardTitle.trim() } : b)),
      );
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) handle401();
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError(null);
    if (passwordForm.next !== passwordForm.confirm) {
      setPasswordError("Passwords do not match.");
      return;
    }
    try {
      await apiChangePassword(token, passwordForm.current, passwordForm.next);
      setPasswordSuccess(true);
      setPasswordForm({ current: "", next: "", confirm: "" });
    } catch (err) {
      if (err instanceof ApiError) setPasswordError(err.message);
      else setPasswordError("Failed to change password.");
    }
  };

  const activeCard = activeCardId ? cardsById[activeCardId] : null;
  const activeBoard = boardSummaries.find((b) => b.id === activeBoardId);

  if (!board) {
    if (loadError) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-4">
          <p className="text-sm text-[var(--gray-text)]">Failed to load board.</p>
          <button
            onClick={() => activeBoardId && loadBoard(activeBoardId)}
            className="rounded-xl bg-[var(--secondary-purple)] px-4 py-2 text-sm font-semibold text-white transition-opacity hover:opacity-90"
          >
            Retry
          </button>
        </div>
      );
    }
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-[var(--gray-text)]">Loading...</p>
      </div>
    );
  }

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[1600px] flex-col gap-10 px-6 pb-16 pt-12">
        <header className="flex flex-col gap-6 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div className="flex-1">
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Project Management
              </p>
              {editingBoardTitle ? (
                <input
                  value={boardTitle}
                  onChange={(e) => setBoardTitle(e.target.value)}
                  onBlur={handleBoardTitleCommit}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleBoardTitleCommit();
                    if (e.key === "Escape") {
                      setBoardTitle(activeBoard?.title ?? "");
                      setEditingBoardTitle(false);
                    }
                  }}
                  className="mt-3 w-full bg-transparent font-display text-4xl font-semibold text-[var(--navy-dark)] outline-none"
                  autoFocus
                />
              ) : (
                <h1
                  className="mt-3 cursor-pointer font-display text-4xl font-semibold text-[var(--navy-dark)] hover:text-[var(--primary-blue)]"
                  onClick={() => setEditingBoardTitle(true)}
                  title="Click to rename board"
                >
                  {boardTitle || "Kanban Studio"}
                </h1>
              )}
            </div>
            <div className="flex flex-col items-end gap-3">
              {/* Board selector */}
              <div className="relative" ref={boardMenuRef}>
                <button
                  onClick={() => setShowBoardMenu((v) => !v)}
                  className="flex items-center gap-2 rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-2 text-sm font-semibold text-[var(--navy-dark)] transition hover:border-[var(--primary-blue)]"
                >
                  <span>Boards ({boardSummaries.length})</span>
                  <span className="text-[var(--gray-text)]">▾</span>
                </button>
                {showBoardMenu && (
                  <div className="absolute right-0 top-full z-20 mt-2 w-64 rounded-2xl border border-[var(--stroke)] bg-white shadow-[var(--shadow)]">
                    <div className="max-h-48 overflow-y-auto p-2">
                      {boardSummaries.map((b) => (
                        <div
                          key={b.id}
                          className="flex items-center justify-between gap-2 rounded-xl px-3 py-2 transition hover:bg-[var(--surface)]"
                        >
                          <button
                            onClick={() => handleSwitchBoard(b.id)}
                            className={`flex-1 text-left text-sm font-medium ${
                              b.id === activeBoardId
                                ? "font-semibold text-[var(--primary-blue)]"
                                : "text-[var(--navy-dark)]"
                            }`}
                          >
                            {b.id === activeBoardId && "✓ "}
                            {b.title}
                          </button>
                          {boardSummaries.length > 1 && (
                            <button
                              onClick={() => handleDeleteBoard(b.id)}
                              className="rounded p-1 text-xs text-[var(--gray-text)] transition hover:text-red-500"
                              title="Delete board"
                            >
                              ✕
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                    <div className="border-t border-[var(--stroke)] p-2">
                      {showNewBoardForm ? (
                        <div className="flex gap-2">
                          <input
                            value={newBoardTitle}
                            onChange={(e) => setNewBoardTitle(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") handleCreateBoard();
                              if (e.key === "Escape") setShowNewBoardForm(false);
                            }}
                            placeholder="Board name"
                            autoFocus
                            className="flex-1 rounded-lg border border-[var(--stroke)] bg-[var(--surface)] px-2 py-1 text-sm outline-none focus:border-[var(--primary-blue)]"
                          />
                          <button
                            onClick={handleCreateBoard}
                            className="rounded-lg bg-[var(--secondary-purple)] px-3 py-1 text-xs font-semibold text-white transition hover:brightness-110"
                          >
                            Add
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setShowNewBoardForm(true)}
                          className="w-full rounded-xl px-3 py-2 text-left text-sm font-semibold text-[var(--primary-blue)] transition hover:bg-[var(--surface)]"
                        >
                          + New board
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
              {/* User controls */}
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    setShowPasswordForm((v) => !v);
                    setPasswordSuccess(false);
                    setPasswordError(null);
                  }}
                  className="rounded-xl border border-[var(--stroke)] bg-white px-4 py-2 text-xs font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)] transition-colors hover:border-[var(--primary-blue)] hover:text-[var(--primary-blue)]"
                >
                  {username}
                </button>
                {onLogout && (
                  <button
                    onClick={onLogout}
                    className="rounded-xl border border-[var(--stroke)] bg-white px-4 py-2 text-xs font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)] transition-colors hover:border-[var(--secondary-purple)] hover:text-[var(--secondary-purple)]"
                  >
                    Sign out
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Password change form */}
          {showPasswordForm && (
            <div className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] p-6">
              <h3 className="mb-4 text-sm font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
                Change Password
              </h3>
              {passwordSuccess ? (
                <p className="text-sm font-semibold text-green-600">
                  Password changed successfully.{" "}
                  <button
                    onClick={() => setShowPasswordForm(false)}
                    className="underline"
                  >
                    Close
                  </button>
                </p>
              ) : (
                <form onSubmit={handleChangePassword} className="flex flex-wrap gap-4">
                  <input
                    type="password"
                    placeholder="Current password"
                    value={passwordForm.current}
                    onChange={(e) => setPasswordForm((p) => ({ ...p, current: e.target.value }))}
                    required
                    className="rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm outline-none focus:border-[var(--primary-blue)]"
                  />
                  <input
                    type="password"
                    placeholder="New password"
                    value={passwordForm.next}
                    onChange={(e) => setPasswordForm((p) => ({ ...p, next: e.target.value }))}
                    required
                    className="rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm outline-none focus:border-[var(--primary-blue)]"
                  />
                  <input
                    type="password"
                    placeholder="Confirm new password"
                    value={passwordForm.confirm}
                    onChange={(e) => setPasswordForm((p) => ({ ...p, confirm: e.target.value }))}
                    required
                    className="rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm outline-none focus:border-[var(--primary-blue)]"
                  />
                  {passwordError && (
                    <p className="w-full text-sm text-red-600">{passwordError}</p>
                  )}
                  <button
                    type="submit"
                    className="rounded-xl bg-[var(--secondary-purple)] px-4 py-2 text-xs font-semibold text-white transition hover:brightness-110"
                  >
                    Update password
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowPasswordForm(false)}
                    className="rounded-xl border border-[var(--stroke)] px-4 py-2 text-xs font-semibold text-[var(--gray-text)] transition hover:text-[var(--navy-dark)]"
                  >
                    Cancel
                  </button>
                </form>
              )}
            </div>
          )}

          {/* Search bar */}
          <div className="flex items-center gap-3">
            <div className="relative flex-1 max-w-md">
              <input
                type="search"
                placeholder="Search cards..."
                value={searchQuery}
                onChange={(e) => handleSearch(e.target.value)}
                className="w-full rounded-xl border border-[var(--stroke)] bg-white px-4 py-2 pl-9 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
              />
              <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--gray-text)]">
                ⌕
              </span>
            </div>
            <button
              onClick={handleShowArchive}
              className="rounded-xl border border-[var(--stroke)] bg-white px-4 py-2 text-xs font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)] transition hover:border-[var(--primary-blue)] hover:text-[var(--primary-blue)]"
            >
              Archive
            </button>
          </div>

          {/* Column pills */}
          <div className="flex flex-wrap items-center gap-4">
            {board.columns.map((column) => (
              <div
                key={column.id}
                className="flex items-center gap-2 rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)]"
              >
                <span className="h-2 w-2 rounded-full bg-[var(--accent-yellow)]" />
                {column.title}
              </div>
            ))}
            <button
              onClick={handleAddColumn}
              className="flex items-center gap-2 rounded-full border border-dashed border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--primary-blue)] transition hover:border-[var(--primary-blue)]"
            >
              + Add column
            </button>
          </div>
        </header>

        {/* WIP limit edit modal */}
        {wipEditingColId && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={() => setWipEditingColId(null)}>
            <div className="rounded-2xl border border-[var(--stroke)] bg-white p-6 shadow-[var(--shadow)] w-72" onClick={(e) => e.stopPropagation()}>
              <h3 className="mb-4 text-sm font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
                WIP Limit
              </h3>
              <p className="mb-3 text-xs text-[var(--gray-text)]">Set the max number of cards in this column (leave blank to remove).</p>
              <input
                type="number"
                min={1}
                value={wipInputValue}
                onChange={(e) => setWipInputValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSetWipLimit(wipEditingColId, wipInputValue);
                  if (e.key === "Escape") setWipEditingColId(null);
                }}
                placeholder="e.g. 3"
                autoFocus
                className="w-full rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2 text-sm outline-none focus:border-[var(--primary-blue)]"
              />
              <div className="mt-4 flex gap-2">
                <button
                  onClick={() => handleSetWipLimit(wipEditingColId, wipInputValue)}
                  className="rounded-xl bg-[var(--secondary-purple)] px-4 py-2 text-xs font-semibold text-white transition hover:brightness-110"
                >
                  Save
                </button>
                <button
                  onClick={() => setWipEditingColId(null)}
                  className="rounded-xl border border-[var(--stroke)] px-4 py-2 text-xs font-semibold text-[var(--gray-text)] transition hover:text-[var(--navy-dark)]"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Archive panel */}
        {showArchive && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={() => setShowArchive(false)}>
            <div className="rounded-2xl border border-[var(--stroke)] bg-white p-6 shadow-[var(--shadow)] w-full max-w-lg max-h-[80vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
                  Archived Cards ({archivedCards.length})
                </h3>
                <button onClick={() => setShowArchive(false)} className="text-[var(--gray-text)] hover:text-[var(--navy-dark)]">✕</button>
              </div>
              <div className="flex-1 overflow-y-auto space-y-3">
                {archivedCards.length === 0 ? (
                  <p className="text-sm text-[var(--gray-text)] text-center py-8">No archived cards.</p>
                ) : (
                  archivedCards.map((card) => (
                    <div key={card.id} className="flex items-start justify-between gap-3 rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-3">
                      <div>
                        <p className="text-xs text-[var(--gray-text)] mb-1">{card.column_title}</p>
                        <p className="text-sm font-semibold text-[var(--navy-dark)]">{card.title}</p>
                        {card.details && <p className="mt-1 text-xs text-[var(--gray-text)]">{card.details}</p>}
                      </div>
                      <button
                        onClick={() => handleUnarchive(card.id)}
                        className="shrink-0 rounded-lg border border-[var(--stroke)] px-3 py-1 text-xs font-semibold text-[var(--primary-blue)] transition hover:border-[var(--primary-blue)]"
                      >
                        Restore
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* Search results overlay */}
        {searchResults !== null && (
          <div className="rounded-2xl border border-[var(--stroke)] bg-white p-6 shadow-[var(--shadow)]">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
                Search Results ({searchResults.length})
              </h3>
              <button
                onClick={() => { setSearchResults(null); setSearchQuery(""); }}
                className="text-xs text-[var(--gray-text)] hover:text-[var(--navy-dark)]"
              >
                Clear
              </button>
            </div>
            {searchResults.length === 0 ? (
              <p className="text-sm text-[var(--gray-text)]">No cards found.</p>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {searchResults.map((card) => (
                  <div key={card.id} className="rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-3">
                    <p className="text-xs text-[var(--gray-text)] mb-1">{card.column_title}</p>
                    <p className="text-sm font-semibold text-[var(--navy-dark)]">{card.title}</p>
                    {card.priority && <p className="mt-1 text-xs font-semibold capitalize text-orange-600">{card.priority}</p>}
                    {card.details && <p className="mt-1 text-xs text-[var(--gray-text)] line-clamp-2">{card.details}</p>}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {board.columns.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-4 rounded-3xl border border-dashed border-[var(--stroke)] py-24">
            <p className="text-sm font-semibold text-[var(--gray-text)]">
              This board has no columns yet.
            </p>
            <button
              onClick={handleAddColumn}
              className="rounded-xl bg-[var(--secondary-purple)] px-6 py-3 text-sm font-semibold text-white transition hover:brightness-110"
            >
              Add your first column
            </button>
          </div>
        ) : (
          <DndContext
            sensors={sensors}
            collisionDetection={closestCorners}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <section
              className="grid gap-6"
              style={{
                gridTemplateColumns: `repeat(${Math.min(board.columns.length, 5)}, minmax(0, 1fr))`,
              }}
            >
              {board.columns.map((column) => (
                <KanbanColumn
                  key={column.id}
                  column={column}
                  cards={column.cardIds.map((cardId) => board.cards[cardId]).filter(Boolean)}
                  onRename={handleRenameColumn}
                  onRenameCommit={handleRenameColumnCommit}
                  onAddCard={handleAddCard}
                  onDeleteCard={handleDeleteCard}
                  onEditCard={handleEditCard}
                  onArchiveCard={handleArchiveCard}
                  onDeleteColumn={handleDeleteColumn}
                  onEditWipLimit={(columnId) => {
                    setWipEditingColId(columnId);
                    const col = board.columns.find((c) => c.id === columnId);
                    setWipInputValue(col?.wip_limit?.toString() ?? "");
                  }}
                />
              ))}
            </section>
            <DragOverlay>
              {activeCard ? (
                <div className="w-[260px]">
                  <KanbanCardPreview card={activeCard} />
                </div>
              ) : null}
            </DragOverlay>
          </DndContext>
        )}
      </main>
    </div>
  );
};
