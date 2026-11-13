// Typed wrappers for /api/v1/process (ADR-005), built on lib/api.ts.
import { apiFetch } from "../api";
import type {
  CharacteristicDetail,
  Line,
  LineOverview,
  OperationSummary,
  PieceTrace,
  ProcessFilters,
} from "./types";

function query(filters: ProcessFilters, extra: Record<string, string> = {}): string {
  const params = new URLSearchParams(extra);
  if (filters.from) params.set("from", filters.from);
  if (filters.to) params.set("to", filters.to);
  filters.recipeIds.forEach((id) => params.append("recipe_id", id));
  const text = params.toString();
  return text ? `?${text}` : "";
}

export function getLines(): Promise<Line[]> {
  return apiFetch("/process/lines");
}

export function getLineOverview(lineId: string, filters: ProcessFilters): Promise<LineOverview> {
  return apiFetch(`/process/lines/${lineId}/overview${query(filters)}`);
}

export function getOperationSummary(operationId: string, filters: ProcessFilters): Promise<OperationSummary> {
  return apiFetch(`/process/operations/${operationId}/summary${query(filters)}`);
}

export function getCharacteristicDetail(
  operationId: string,
  characteristicId: string,
  filters: ProcessFilters,
): Promise<CharacteristicDetail> {
  return apiFetch(
    `/process/operations/${operationId}/characteristics/${characteristicId}${query(filters, { bins: "30" })}`,
  );
}

export function getPieceTrace(serialNumber: string): Promise<PieceTrace> {
  return apiFetch(`/process/pieces/${encodeURIComponent(serialNumber)}`);
}
