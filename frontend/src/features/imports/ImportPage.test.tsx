import { describe, expect, it } from "vitest";
import { fireEvent, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Routes, Route } from "react-router-dom";
import { http, HttpResponse } from "msw";
import { renderAuthed } from "../../test/renderAuthed";
import { server, METROLOGIST_EMAIL, METROLOGIST_PASSWORD, VALID_EMAIL, VALID_PASSWORD } from "../../test/server";
import { ImportPage } from "./ImportPage";

const API_BASE_URL = "http://localhost:8000/api/v1";

function renderPage(credentials: { email: string; password: string }) {
  return renderAuthed(
    <Routes>
      <Route path="/imports" element={<ImportPage />} />
    </Routes>,
    { ...credentials, route: "/imports" },
  );
}

function makeFile(name: string, content = "part_number,COL_1\nMI-DEMO-1001,10.02\n", type = "text/csv") {
  return new File([content], name, { type });
}

function fileInput(): HTMLInputElement {
  return document.querySelector('input[type="file"]') as HTMLInputElement;
}

describe("ImportPage", () => {
  it("disables the dropzone for a non-metrologist/admin role", async () => {
    renderPage({ email: VALID_EMAIL, password: VALID_PASSWORD });

    await screen.findByText(/only metrologist or admin/i);
    expect(screen.getByRole("button")).toHaveAttribute("aria-disabled", "true");
  });

  it("rejects an unsupported file type dropped in, without a network call", async () => {
    // Dropped via drag-and-drop, not the file-picker input: a picker
    // constrained by `accept=".csv,.xlsx"` wouldn't offer a .txt file at all,
    // but a drop always bypasses that filter -- exactly the case client-side
    // validation exists to catch.
    let called = false;
    server.use(
      http.post(`${API_BASE_URL}/imports`, () => {
        called = true;
        return HttpResponse.json({});
      }),
    );
    renderPage({ email: METROLOGIST_EMAIL, password: METROLOGIST_PASSWORD });
    await screen.findByText(/drag and drop/i);

    fireEvent.drop(screen.getByRole("button"), {
      dataTransfer: { files: [makeFile("notes.txt", "hello", "text/plain")] },
    });

    expect(await screen.findByRole("alert")).toHaveTextContent(/unsupported file type/i);
    expect(called).toBe(false);
  });

  it("uploads a valid file and shows the parsed result", async () => {
    const user = userEvent.setup();
    server.use(
      http.post(`${API_BASE_URL}/imports`, () =>
        HttpResponse.json(
          {
            id: "file-1",
            original_filename: "mi_demo_1001_import_batch.csv",
            sha256: "a".repeat(64),
            size_bytes: 855,
            content_type: "text/csv",
            parse_status: "parsed",
            error_detail: null,
            created_at: "2026-07-13T10:00:00Z",
            runs_created: 1,
            samples_created: 4,
            results_created: 12,
            quarantined_rows: [],
          },
          { status: 201 },
        ),
      ),
    );
    renderPage({ email: METROLOGIST_EMAIL, password: METROLOGIST_PASSWORD });
    await screen.findByText(/drag and drop/i);

    await user.upload(fileInput(), makeFile("mi_demo_1001_import_batch.csv"));

    expect(await screen.findByText("mi_demo_1001_import_batch.csv")).toBeInTheDocument();
    expect(screen.getByText("Parsed")).toBeInTheDocument();
    expect(screen.getByText(/1 runs · 12 results/)).toBeInTheDocument();
  });

  it("shows quarantined rows with their reasons, expandable", async () => {
    const user = userEvent.setup();
    server.use(
      http.post(`${API_BASE_URL}/imports`, () =>
        HttpResponse.json(
          {
            id: "file-2",
            original_filename: "partial.csv",
            sha256: "b".repeat(64),
            size_bytes: 500,
            content_type: "text/csv",
            parse_status: "parsed",
            error_detail: null,
            created_at: "2026-07-13T10:00:00Z",
            runs_created: 1,
            samples_created: 2,
            results_created: 4,
            quarantined_rows: [{ id: "q1", row_number: 3, raw_row: {}, reason: "Unknown part_number 'MI-DEMO-9999'." }],
          },
          { status: 201 },
        ),
      ),
    );
    renderPage({ email: METROLOGIST_EMAIL, password: METROLOGIST_PASSWORD });
    await screen.findByText(/drag and drop/i);

    await user.upload(fileInput(), makeFile("partial.csv"));
    await screen.findByText("partial.csv");
    await user.click(screen.getByRole("button", { name: /view quarantined rows/i }));

    expect(await screen.findByText(/Unknown part_number/)).toBeInTheDocument();
  });

  it("shows a clean message on a duplicate-file 409", async () => {
    const user = userEvent.setup();
    server.use(
      http.post(`${API_BASE_URL}/imports`, () =>
        HttpResponse.json(
          { detail: { message: "This file has already been imported.", imported_file_id: "existing-id" } },
          { status: 409 },
        ),
      ),
    );
    renderPage({ email: METROLOGIST_EMAIL, password: METROLOGIST_PASSWORD });
    await screen.findByText(/drag and drop/i);

    await user.upload(fileInput(), makeFile("dup.csv"));

    expect(await screen.findByRole("alert")).toHaveTextContent("This file has already been imported.");
  });
});
