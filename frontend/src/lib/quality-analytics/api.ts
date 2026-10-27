import { apiFetch } from "../api";
import { filterParams, type QualityFilters } from "./filters";
import type { OverviewResponse, QualityDataset, ReportSummary, VariableDetailResponse } from "./types";

// IQ-F5: single boundary for /api/v1/quality-analytics.

export function fetchDatasets(): Promise<{ items: QualityDataset[] }> {
  return apiFetch<{ items: QualityDataset[] }>("/quality-analytics/datasets");
}

export function fetchOverview(f: QualityFilters): Promise<OverviewResponse> {
  const params = filterParams(f);
  params.set("granularity", f.granularity);
  if (f.variables.length) params.set("variables", f.variables.join(","));
  return apiFetch<OverviewResponse>(`/quality-analytics/overview?${params.toString()}`);
}

export function fetchVariableDetail(f: QualityFilters): Promise<VariableDetailResponse> {
  const params = filterParams(f);
  params.set("variable", f.detailVariable);
  params.set("group_by", f.groupBy);
  return apiFetch<VariableDetailResponse>(`/quality-analytics/variable?${params.toString()}`);
}

export function fetchReportSummary(): Promise<ReportSummary> {
  return apiFetch<ReportSummary>("/quality-analytics/report-summary");
}
