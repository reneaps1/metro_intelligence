import { Fragment } from "react";
import { Link } from "react-router-dom";
import { ChevronDown, ChevronRight } from "lucide-react";
import { StatusChip } from "../../components/ui/StatusChip";
import { STATUS_LABEL, formatCount, formatPercent, operationKindLabel } from "../../lib/process/format";
import type { StepOverview } from "../../lib/process/types";

// Process flow (ADR-005): the line's steps in sequence, each a link to its
// detail. Horizontal row on wide screens, vertical stack on narrow ones; the
// connectors are plain icons so the flow needs no diagram library.
export function ProcessFlow({ steps, search }: { steps: StepOverview[]; search: string }) {
  const ordered = [...steps].sort((a, b) => a.operation.sequence - b.operation.sequence);

  return (
    <ol className="flex flex-col gap-2 lg:flex-row lg:items-stretch lg:gap-0" aria-label="Process steps in order">
      {ordered.map((step, index) => (
        <Fragment key={step.operation.id}>
          <li className="min-w-0 lg:flex-1">
            <StepNode step={step} search={search} />
          </li>
          {index < ordered.length - 1 && (
            <li aria-hidden="true" className="flex items-center justify-center text-text-disabled lg:px-1">
              <ChevronDown size={20} className="lg:hidden" />
              <ChevronRight size={20} className="hidden lg:block" />
            </li>
          )}
        </Fragment>
      ))}
    </ol>
  );
}

function StepNode({ step, search }: { step: StepOverview; search: string }) {
  const { operation } = step;
  const nokRate = step.has_specification ? step.spec_nok_rate : step.machine_nok_rate;
  const nokLabel = step.has_specification ? "Out of drawing" : "Station NOK";
  const partialCoverage = step.coverage !== null && step.coverage < 0.95;

  return (
    <Link
      to={`/process/operations/${operation.id}${search}`}
      className="flex h-full min-h-[44px] flex-col gap-2 rounded border border-border bg-surface p-3 transition-colors hover:border-brand-primary focus-visible:border-brand-primary"
    >
      <div className="flex items-start justify-between gap-2">
        <span className="font-mono text-xs text-text-secondary">{String(operation.sequence).padStart(2, "0")}</span>
        <StatusChip status={step.status} label={STATUS_LABEL[step.status]} />
      </div>
      <div className="min-w-0">
        <p className="text-sm font-semibold text-text-primary">{operation.name}</p>
        <p className="text-xs text-text-secondary">{operationKindLabel(operation)}</p>
      </div>
      <dl className="mt-auto grid grid-cols-2 gap-x-2 gap-y-1 text-xs">
        <dt className="text-text-secondary">Pieces</dt>
        <dd className="text-right font-mono text-text-primary">{formatCount(step.pieces)}</dd>
        <dt className="text-text-secondary">{nokLabel}</dt>
        <dd className="text-right font-mono text-text-primary">{formatPercent(nokRate)}</dd>
        {step.disagreements > 0 && (
          <>
            <dt className="text-text-secondary">Station OK, drawing NOK</dt>
            <dd className="text-right font-mono text-status-warning">{formatCount(step.disagreements)}</dd>
          </>
        )}
      </dl>
      {partialCoverage && (
        <p className="text-xs text-text-secondary">Logs {formatPercent(step.coverage, 1)} of pieces</p>
      )}
    </Link>
  );
}
