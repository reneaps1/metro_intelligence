// F5.6 (MI-35): mirrors backend/app/schemas/imports.py (F4.5).
export interface QuarantinedRow {
  id: string;
  row_number: number;
  raw_row: Record<string, unknown>;
  reason: string;
}

export type ParseStatus = "parsing" | "parsed" | "quarantined" | "error";

export interface ImportedFile {
  id: string;
  original_filename: string;
  sha256: string;
  size_bytes: number;
  content_type: string | null;
  parse_status: ParseStatus;
  error_detail: string | null;
  created_at: string;
  runs_created: number;
  samples_created: number;
  results_created: number;
  quarantined_rows: QuarantinedRow[];
}
