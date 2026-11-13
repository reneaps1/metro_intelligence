import { apiFetch } from "../api";

// IQ-F1 (docs/tasks/IQ-plan-demo-industrial-quality.md, D5): the edition is
// read from the backend at runtime so one frontend build serves both.
export type Edition = "metrology" | "industrial";

export interface MetaResponse {
  edition: Edition;
  client_label: string | null;
  modules: string[];
}

export function fetchMeta(): Promise<MetaResponse> {
  return apiFetch<MetaResponse>("/meta");
}
