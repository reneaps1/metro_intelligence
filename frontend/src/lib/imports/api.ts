import { apiFetch } from "../api";
import type { ImportedFile } from "./types";

// Mirrors backend/app/connectors/manual_upload.py (accepted extensions) and
// backend/app/services/import_service.py's MAX_FILE_SIZE_BYTES. Client-side
// checks are defense in depth (CLAUDE.md §5) -- the real validation is F4.5's,
// re-run server-side regardless of what the client thinks it uploaded.
export const ACCEPTED_EXTENSIONS = [".csv", ".xlsx"];
export const MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024;

export function validateFileClientSide(file: File): string | null {
  const name = file.name.toLowerCase();
  if (!ACCEPTED_EXTENSIONS.some((ext) => name.endsWith(ext))) {
    return `Unsupported file type. Allowed: ${ACCEPTED_EXTENSIONS.join(", ")}.`;
  }
  if (file.size > MAX_FILE_SIZE_BYTES) {
    return `File exceeds the maximum allowed size of ${MAX_FILE_SIZE_BYTES / (1024 * 1024)} MB.`;
  }
  if (file.size === 0) {
    return "File is empty.";
  }
  return null;
}

export function uploadImport(file: File): Promise<ImportedFile> {
  const form = new FormData();
  form.append("file", file);
  return apiFetch<ImportedFile>("/imports", { method: "POST", body: form });
}
