import { Fragment } from "react";
import { Link } from "react-router-dom";
import { ChevronDown, ChevronRight } from "lucide-react";
import { StatusChip } from "../../components/ui/StatusChip";
import {
  formatCount,
  formatDayWithYear,
  formatPercent,
  operationKindLabel,
  stepStatusLabel,
} from "../../lib/process/format";
import type { StepOverview } from "../../lib/process/types";

// Process flow (ADR-005): the line's steps in sequence, each a link to its
// detail. Horizontal row on wide screens, vertical stack on narrow ones; the
// connectors are plain icons so the flow needs no diagram library.
export function ProcessFlow({
  steps,
  search,
}: {
  steps: StepOverview[];
  search: string;
}) {
  const ordered = [...steps].sort(
    (a, b) => a.operation.sequence - b.operation.sequence,
  );

  return (
    <ol
      className="flex flex-col gap-2 lg:flex-row lg:items-stretch lg:gap-0"
      aria-label="Process steps in order"
    >
      {ordered.map((step, index) => (
        <Fragment key={step.operation.id}>
          <li className="min-w-0 lg:flex-1">
            <StepNode step={step} search={search} />
          </li>
          {index < ordered.length - 1 && (
            <li
              aria-hidden="true"
              className="flex items-center justify-center text-text-disabled"
            >
              <ChevronDown size={20} className="lg:hidden" />
              <ChevronRight size={16} className="hidden lg:block" />
            </li>
          )}
        </Fragment>
      ))}
    </ol>
  );
}

// The cards are narrow: the longest status gets a one-word form here (the
// full text is the tooltip and what the table below shows).
const CARD_LABEL: Record<string, string> = { "Action needed": "Action" };

function StepNode({ step, search }: { step: StepOverview; search: string }) {
  const { operation } = step;
  const nokRate = step.has_specification ? step.spec_nok_rate : step.machine_nok_rate;
  const empty = step.pieces === 0;

  // Every card has the same blocks at the same height: number, name (two
  // lines reserved), status, then the same three rows, so the steps compare
  // at a glance.
  return (
    <Link
      to={`/process/operations/${operation.id}${search}`}
      className="flex h-full min-h-[44px] flex-col gap-2 rounded border border-border bg-surface p-3 transition-colors hover:border-brand-primary focus-visible:border-brand-primary"
    >
      <span className="font-mono text-xs text-text-secondary">{String(operation.sequence).padStart(2, "0")}</span>
      <div className="min-w-0 lg:min-h-[5rem]">
        <p className="text-sm font-semibold text-text-primary">{operation.name}</p>
        <p className="text-xs text-text-secondary">{operationKindLabel(operation)}</p>
      </div>
      <div className="whitespace-nowrap" title={stepStatusLabel(step)}>
        <StatusChip status={step.status} label={CARD_LABEL[stepStatusLabel(step)] ?? stepStatusLabel(step)} />
      </div>
      {empty ? (
        <p className="text-xs text-text-secondary">
          No data in this range
          {step.last_day && (
            <>
              <br />
              Last data <span className="font-mono">{formatDayWithYear(step.last_day)}</span>
            </>
          )}
        </p>
      ) : (
        <dl className="grid grid-cols-[1fr_auto] gap-x-2 gap-y-1 text-xs">
          <dt className="text-text-secondary">Pieces</dt>
          <dd className="text-right font-mono text-text-primary">{formatCount(step.pieces)}</dd>
          <dt className="text-text-secondary">NOK</dt>
          <dd className="text-right font-mono text-text-primary">{formatPercent(nokRate)}</dd>
          <dt className="whitespace-nowrap text-text-secondary">1st pass</dt>
          <dd className="text-right font-mono text-text-primary">{formatPercent(step.first_pass_yield, 1)}</dd>
        </dl>
      )}
      {!empty && (
        <p className="whitespace-nowrap text-xs text-text-secondary">
          NOK per {step.has_specification ? "drawing" : "station"}
        </p>
      )}
      {!empty && step.partial_logging && (
        <p className="text-xs text-text-secondary">Logs {formatPercent(step.coverage, 1)} of pieces</p>
      )}
      {!empty && step.disagreements > 0 && (
        <p className="text-xs text-status-warning">
          <span className="font-mono">{formatCount(step.disagreements)}</span> station OK, drawing NOK
        </p>
      )}
    </Link>
  );
}
