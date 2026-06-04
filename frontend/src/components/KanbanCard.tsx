import { useState } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import clsx from "clsx";
import type { Card } from "@/lib/kanban";
import { CardComments } from "@/components/CardComments";

const LABEL_COLORS: Record<string, string> = {
  urgent: "bg-red-100 text-red-700",
  bug: "bg-orange-100 text-orange-700",
  feature: "bg-blue-100 text-blue-700",
  docs: "bg-green-100 text-green-700",
  chore: "bg-gray-100 text-gray-600",
};

const PRIORITY_CONFIG: Record<string, { color: string; dot: string }> = {
  low: { color: "text-gray-400", dot: "bg-gray-300" },
  medium: { color: "text-yellow-600", dot: "bg-yellow-400" },
  high: { color: "text-orange-600", dot: "bg-orange-400" },
  critical: { color: "text-red-600", dot: "bg-red-500" },
};

function isOverdue(due_date: string | null): boolean {
  if (!due_date) return false;
  return new Date(due_date) < new Date(new Date().toDateString());
}

type KanbanCardProps = {
  card: Card;
  token: string;
  username: string;
  onDelete: (cardId: string) => void;
  onEdit: (cardId: string, title: string, details: string) => void;
  onArchive: (cardId: string) => void;
};

export const KanbanCard = ({ card, token, username, onDelete, onEdit, onArchive }: KanbanCardProps) => {
  const [editing, setEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(card.title);
  const [editDetails, setEditDetails] = useState(card.details);
  const [showComments, setShowComments] = useState(false);

  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: card.id, data: { type: "card" } });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const handleEditSave = () => {
    const t = editTitle.trim();
    const d = editDetails.trim();
    if (t) onEdit(card.id, t, d);
    setEditing(false);
  };

  const handleEditCancel = () => {
    setEditTitle(card.title);
    setEditDetails(card.details);
    setEditing(false);
  };

  const labelClass = card.label ? (LABEL_COLORS[card.label] ?? "bg-gray-100 text-gray-600") : null;
  const priorityCfg = card.priority ? PRIORITY_CONFIG[card.priority] : null;
  const overdue = isOverdue(card.due_date);

  if (editing) {
    return (
      <article
        ref={setNodeRef}
        style={style}
        className="rounded-2xl border border-[var(--primary-blue)] bg-white px-4 py-4 shadow-[0_12px_24px_rgba(3,33,71,0.08)]"
        data-testid={`card-${card.id}`}
      >
        <div className="flex flex-col gap-2">
          <input
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            className="w-full rounded-lg border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2 text-sm font-semibold text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
            placeholder="Card title"
            autoFocus
          />
          <textarea
            value={editDetails}
            onChange={(e) => setEditDetails(e.target.value)}
            rows={2}
            className="w-full resize-none rounded-lg border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2 text-xs text-[var(--gray-text)] outline-none focus:border-[var(--primary-blue)]"
            placeholder="Details"
          />
          <CardComments token={token} cardId={card.id} username={username} />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleEditSave}
              className="rounded-full bg-[var(--secondary-purple)] px-3 py-1 text-xs font-semibold text-white transition hover:brightness-110"
            >
              Save
            </button>
            <button
              type="button"
              onClick={handleEditCancel}
              className="rounded-full border border-[var(--stroke)] px-3 py-1 text-xs font-semibold text-[var(--gray-text)] transition hover:text-[var(--navy-dark)]"
            >
              Close
            </button>
          </div>
        </div>
      </article>
    );
  }

  return (
    <article
      ref={setNodeRef}
      style={style}
      className={clsx(
        "rounded-2xl border border-transparent bg-white px-4 py-4 shadow-[0_12px_24px_rgba(3,33,71,0.08)]",
        "transition-all duration-150",
        isDragging && "opacity-60 shadow-[0_18px_32px_rgba(3,33,71,0.16)]",
        overdue && !isDragging && "border border-red-200 bg-red-50",
      )}
      {...attributes}
      {...listeners}
      data-testid={`card-${card.id}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            {labelClass && (
              <span className={clsx("inline-block rounded-full px-2 py-0.5 text-xs font-semibold capitalize", labelClass)}>
                {card.label}
              </span>
            )}
            {priorityCfg && (
              <span className={clsx("flex items-center gap-1 text-xs font-semibold capitalize", priorityCfg.color)}>
                <span className={clsx("h-1.5 w-1.5 rounded-full", priorityCfg.dot)} />
                {card.priority}
              </span>
            )}
            {card.assigned_to && (
              <span className="rounded-full bg-[var(--surface)] px-2 py-0.5 text-xs font-semibold text-[var(--navy-dark)]">
                @{card.assigned_to}
              </span>
            )}
          </div>
          <h4 className="mt-1 font-display text-base font-semibold text-[var(--navy-dark)]">
            {card.title}
          </h4>
          {card.details && (
            <p className="mt-2 text-sm leading-6 text-[var(--gray-text)]">{card.details}</p>
          )}
          {card.due_date && (
            <p className={clsx("mt-2 text-xs font-semibold", overdue ? "text-red-600" : "text-[var(--gray-text)]")}>
              {overdue ? "Overdue: " : "Due: "}{card.due_date}
            </p>
          )}
          {showComments && (
            <div onPointerDown={(e) => e.stopPropagation()}>
              <CardComments token={token} cardId={card.id} username={username} />
            </div>
          )}
        </div>
        <div className="flex flex-col gap-1">
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); setEditing(true); }}
            onPointerDown={(e) => e.stopPropagation()}
            className="rounded-full border border-transparent px-2 py-1 text-xs font-semibold text-[var(--primary-blue)] transition hover:border-[var(--stroke)]"
            aria-label={`Edit ${card.title}`}
          >
            Edit
          </button>
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); setShowComments((v) => !v); }}
            onPointerDown={(e) => e.stopPropagation()}
            className="rounded-full border border-transparent px-2 py-1 text-xs font-semibold text-[var(--gray-text)] transition hover:border-[var(--stroke)] hover:text-[var(--primary-blue)]"
            aria-label={`Comments for ${card.title}`}
          >
            💬
          </button>
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onArchive(card.id); }}
            onPointerDown={(e) => e.stopPropagation()}
            className="rounded-full border border-transparent px-2 py-1 text-xs font-semibold text-[var(--gray-text)] transition hover:border-[var(--stroke)] hover:text-amber-600"
            aria-label={`Archive ${card.title}`}
          >
            Archive
          </button>
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onDelete(card.id); }}
            onPointerDown={(e) => e.stopPropagation()}
            className="rounded-full border border-transparent px-2 py-1 text-xs font-semibold text-[var(--gray-text)] transition hover:border-[var(--stroke)] hover:text-[var(--navy-dark)]"
            aria-label={`Delete ${card.title}`}
          >
            Remove
          </button>
        </div>
      </div>
    </article>
  );
};
