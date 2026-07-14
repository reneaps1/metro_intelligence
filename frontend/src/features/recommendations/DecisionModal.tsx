import { useEffect, useRef, useState } from "react";
import { Button } from "../../components/ui/Button";
import { ApiError } from "../../lib/api";
import type { DecisionAction } from "../../lib/recommendations/types";

// F5.9 (MI-38): no shared Modal exists yet (F5.2 hasn't built one) -- this is
// a small overlay scoped to this feature rather than a premature ui/ addition
// (CLAUDE.md: no speculative abstraction). A real confirmation step matters
// here specifically because accept/reject is an irreversible, traceable
// decision (CLAUDE.md §24), not just another form submit.
export function DecisionModal({
  action,
  submitting,
  error,
  onConfirm,
  onCancel,
}: {
  action: DecisionAction;
  submitting: boolean;
  error: string | null;
  onConfirm: (comment: string) => void;
  onCancel: () => void;
}) {
  const [comment, setComment] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onCancel();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onCancel]);

  const label = action === "accepted" ? "Accept recommendation" : "Reject recommendation";
  const trimmed = comment.trim();

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="decision-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onCancel}
    >
      <div
        className="w-full max-w-md rounded border border-border bg-surface p-5 shadow-md"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="decision-modal-title" className="text-lg font-semibold text-text-primary">
          {label}
        </h2>
        <p className="mt-1 text-sm text-text-secondary">
          This decision is recorded and traceable (CLAUDE.md §23/§24). A reason is required.
        </p>

        <label className="mt-4 block text-xs font-medium text-text-secondary" htmlFor="decision-comment">
          Reason (required)
        </label>
        <textarea
          id="decision-comment"
          ref={textareaRef}
          rows={3}
          className="mt-1 w-full rounded border border-border bg-surface px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-status-info"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder={
            action === "accepted"
              ? "Why does this recommendation make sense?"
              : "Why is this recommendation being rejected?"
          }
        />

        {error && <p className="mt-2 text-sm text-status-nok">{error}</p>}

        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={onCancel} disabled={submitting}>
            Cancel
          </Button>
          <Button
            variant={action === "accepted" ? "primary" : "danger"}
            onClick={() => onConfirm(trimmed)}
            disabled={trimmed.length === 0 || submitting}
            loading={submitting}
          >
            Confirm {action === "accepted" ? "accept" : "reject"}
          </Button>
        </div>
      </div>
    </div>
  );
}

export function errorMessage(err: unknown): string {
  return err instanceof ApiError ? err.message : "Something went wrong. Please try again.";
}
