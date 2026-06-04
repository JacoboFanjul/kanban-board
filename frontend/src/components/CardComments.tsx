"use client";

import { useState, useEffect } from "react";
import { apiGetComments, apiCreateComment, apiDeleteComment, type ApiComment } from "@/lib/api";

interface Props {
  token: string;
  cardId: string;
  username: string;
}

export const CardComments = ({ token, cardId, username }: Props) => {
  const [comments, setComments] = useState<ApiComment[]>([]);
  const [newComment, setNewComment] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    apiGetComments(token, cardId)
      .then(setComments)
      .finally(() => setLoading(false));
  }, [token, cardId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const content = newComment.trim();
    if (!content) return;
    setSubmitting(true);
    try {
      const comment = await apiCreateComment(token, cardId, content);
      setComments((prev) => [...prev, comment]);
      setNewComment("");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (commentId: string) => {
    await apiDeleteComment(token, commentId);
    setComments((prev) => prev.filter((c) => c.id !== commentId));
  };

  const formatDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return iso;
    }
  };

  if (loading) {
    return <p className="mt-3 text-xs text-[var(--gray-text)]">Loading comments…</p>;
  }

  return (
    <div className="mt-4 border-t border-[var(--stroke)] pt-3">
      <p className="mb-2 text-xs font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)]">
        Comments ({comments.length})
      </p>
      <div className="space-y-2 max-h-40 overflow-y-auto">
        {comments.map((c) => (
          <div key={c.id} className="rounded-lg bg-[var(--surface)] px-3 py-2 text-xs">
            <div className="flex items-start justify-between gap-2">
              <div>
                <span className="font-semibold text-[var(--navy-dark)]">{c.username}</span>
                <span className="ml-2 text-[var(--gray-text)]">{formatDate(c.created_at)}</span>
              </div>
              {c.username === username && (
                <button
                  type="button"
                  onClick={() => handleDelete(c.id)}
                  className="shrink-0 text-[var(--gray-text)] transition hover:text-red-500"
                  aria-label="Delete comment"
                >
                  ✕
                </button>
              )}
            </div>
            <p className="mt-1 text-[var(--gray-text)] leading-5">{c.content}</p>
          </div>
        ))}
        {comments.length === 0 && (
          <p className="text-xs text-[var(--gray-text)]">No comments yet.</p>
        )}
      </div>
      <form onSubmit={handleSubmit} className="mt-3 flex gap-2">
        <input
          value={newComment}
          onChange={(e) => setNewComment(e.target.value)}
          placeholder="Add a comment…"
          className="flex-1 rounded-lg border border-[var(--stroke)] bg-white px-3 py-1.5 text-xs outline-none focus:border-[var(--primary-blue)]"
        />
        <button
          type="submit"
          disabled={submitting || !newComment.trim()}
          className="rounded-lg bg-[var(--secondary-purple)] px-3 py-1.5 text-xs font-semibold text-white transition hover:brightness-110 disabled:opacity-50"
        >
          Post
        </button>
      </form>
    </div>
  );
};
