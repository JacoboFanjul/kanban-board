"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
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
  apiRenameColumn,
  apiCreateCard,
  apiDeleteCard,
  apiMoveCard,
  type ApiBoard,
} from "@/lib/api";

interface Props {
  token: string;
  onLogout?: () => void;
}

function normalizeBoard(api: ApiBoard): BoardData {
  const cards: BoardData["cards"] = {};
  const columns = api.columns.map((col) => {
    col.cards.forEach((card) => {
      cards[card.id] = card;
    });
    return { id: col.id, title: col.title, cardIds: col.cards.map((c) => c.id) };
  });
  return { columns, cards };
}

export const KanbanBoard = ({ token, onLogout }: Props) => {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [loadError, setLoadError] = useState(false);

  const handle401 = useCallback(() => {
    onLogout?.();
  }, [onLogout]);

  const loadBoard = useCallback(() => {
    setLoadError(false);
    apiGetBoard(token)
      .then((data) => setBoard(normalizeBoard(data)))
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 401) handle401();
        else setLoadError(true);
      });
  }, [token, handle401]);

  useEffect(() => {
    loadBoard();
  }, [loadBoard]);

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
        ? {
            ...prev,
            columns: prev.columns.map((col) =>
              col.id === columnId ? { ...col, title } : col,
            ),
          }
        : prev,
    );
  };

  const handleRenameColumnCommit = (columnId: string, title: string) => {
    apiRenameColumn(token, columnId, title).catch((err: unknown) => {
      if (err instanceof ApiError && err.status === 401) handle401();
      else loadBoard();
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
                col.id === columnId
                  ? { ...col, cardIds: [...col.cardIds, card.id] }
                  : col,
              ),
            }
          : prev,
      );
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 401) handle401();
    }
  };

  const handleDeleteCard = (columnId: string, cardId: string) => {
    const prevBoard = board;
    setBoard((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        cards: Object.fromEntries(
          Object.entries(prev.cards).filter(([id]) => id !== cardId),
        ),
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

  const activeCard = activeCardId ? cardsById[activeCardId] : null;

  if (!board) {
    if (loadError) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-4">
          <p className="text-sm text-[var(--gray-text)]">Failed to load board.</p>
          <button
            onClick={loadBoard}
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

      <main className="relative mx-auto flex min-h-screen max-w-[1500px] flex-col gap-10 px-6 pb-16 pt-12">
        <header className="flex flex-col gap-6 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Single Board Kanban
              </p>
              <h1 className="mt-3 font-display text-4xl font-semibold text-[var(--navy-dark)]">
                Kanban Studio
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--gray-text)]">
                Keep momentum visible. Rename columns, drag cards between stages,
                and capture quick notes without getting buried in settings.
              </p>
            </div>
            <div className="flex flex-col items-end gap-3">
              <div className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-5 py-4">
                <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                  Focus
                </p>
                <p className="mt-2 text-lg font-semibold text-[var(--primary-blue)]">
                  One board. Five columns. Zero clutter.
                </p>
              </div>
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
          </div>
        </header>

        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <section className="grid gap-6 lg:grid-cols-5">
            {board.columns.map((column) => (
              <KanbanColumn
                key={column.id}
                column={column}
                cards={column.cardIds.map((cardId) => board.cards[cardId])}
                onRename={handleRenameColumn}
                onRenameCommit={handleRenameColumnCommit}
                onAddCard={handleAddCard}
                onDeleteCard={handleDeleteCard}
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
      </main>
    </div>
  );
};
