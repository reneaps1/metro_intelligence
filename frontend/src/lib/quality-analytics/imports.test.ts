import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { API_BASE_URL } from "../api";
import { IMPORT_PREVIEW_FIXTURE, IMPORT_REPORT_FIXTURE, server } from "../../test/server";
import {
  PREVIEW_BYTES,
  createImportedDataset,
  mappingErrors,
  mappingFromPreview,
  mappingPayload,
  parseOptionalNumber,
  sampleNotice,
  uploadForm,
  validateImportFile,
  type ColumnMapping,
  type ImportPreview,
} from "./imports";

const preview = IMPORT_PREVIEW_FIXTURE as ImportPreview;

function wide(overrides: Partial<ColumnMapping> = {}): ColumnMapping {
  return {
    layout: "wide",
    delimiter: ",",
    decimal: ".",
    date_order: "dmy",
    roles: { timestamp: "ts", cavity: "cav" },
    value_columns: ["H", "W"],
    specs: {},
    ...overrides,
  };
}

describe("mapping helpers", () => {
  it("starts from the backend suggestion", () => {
    const m = mappingFromPreview(preview);
    expect(m.layout).toBe("long");
    expect(m.delimiter).toBe(";");
    expect(m.roles.cavity).toBe("Nido");
    expect(mappingErrors(m)).toEqual([]);
  });

  it("flags missing required roles per layout", () => {
    const m = mappingFromPreview(preview);
    expect(mappingErrors({ ...m, roles: { ...m.roles, value: undefined } })).toEqual(["Asigna la columna «Valor medido»."]);
    expect(mappingErrors(wide({ value_columns: [] }))).toContain("Elige al menos una columna de variable.");
  });

  it("flags a column used twice and inverted limits", () => {
    expect(mappingErrors(wide({ roles: { timestamp: "ts", cavity: "ts" } }))).toContain(
      "Una misma columna está asignada a dos campos.",
    );
    expect(mappingErrors(wide({ value_columns: ["cav"] }))).toContain(
      "Una columna de variable también está asignada a otro campo.",
    );
    expect(mappingErrors(wide({ specs: { H: { nominal: null, lsl: 3, usl: 2, unit: null } } }))).toEqual([
      "«H»: el LIE es mayor que el LSE.",
    ]);
  });

  it("builds a payload that drops roles of the other layout and empty specs", () => {
    const m = wide({
      roles: { timestamp: "ts", cavity: "cav", variable: "leftover" },
      specs: {
        H: { nominal: 2.5, lsl: 2.47, usl: 2.53, unit: "mm" },
        W: { nominal: null, lsl: null, usl: null, unit: null },
        gone: { nominal: 1, lsl: null, usl: null, unit: null },
      },
    });
    const body = mappingPayload(m);
    expect(body.variable).toBeUndefined();
    expect(body.timestamp).toBe("ts");
    expect(body.piece_id).toBeNull();
    expect(body.specs).toEqual({ H: { nominal: 2.5, lsl: 2.47, usl: 2.53, unit: "mm" } });
    expect(mappingPayload(mappingFromPreview(preview)).value_columns).toEqual([]);
  });

  it("describes a sample honestly", () => {
    expect(sampleNotice(IMPORT_REPORT_FIXTURE as never)).toMatch(/^Muestra de 5,761 filas \(~13 % del archivo\)/);
    expect(sampleNotice({ ...IMPORT_REPORT_FIXTURE, sample: { ...IMPORT_REPORT_FIXTURE.sample, limited: false } } as never)).toBeNull();
  });

  it("parses optional numbers with either decimal mark", () => {
    expect(parseOptionalNumber("0,625")).toBeCloseTo(0.625);
    expect(parseOptionalNumber(" 2.5 ")).toBe(2.5);
    expect(parseOptionalNumber("")).toBeNull();
    expect(parseOptionalNumber("-")).toBeNull();
  });

  it("validates the file type before uploading", () => {
    expect(validateImportFile(new File(["a"], "x.xlsx"))).toMatch(/\.csv/);
    expect(validateImportFile(new File([], "x.csv"))).toMatch(/vacío/);
    expect(validateImportFile(new File(["a,b"], "x.CSV"))).toBeNull();
  });
});

describe("upload boundary", () => {
  it("sends only the head of a large file plus its real size", () => {
    const big = new File(["x".repeat(PREVIEW_BYTES + 1000)], "big.csv", { type: "text/csv" });
    const body = uploadForm(big, PREVIEW_BYTES, { delimiter: ";" });
    const file = body.get("file") as File;
    expect(file.size).toBe(PREVIEW_BYTES);
    expect(file.name).toBe("big.csv");
    expect(body.get("file_size")).toBe(String(PREVIEW_BYTES + 1000));
    expect(body.get("delimiter")).toBe(";");
  });

  it("sends a small file whole", () => {
    const small = new File(["a,b\n1,2\n"], "s.csv");
    expect((uploadForm(small, PREVIEW_BYTES, {}).get("file") as File).size).toBe(small.size);
  });

  it("returns the report even when no dataset survived validation", async () => {
    server.use(
      http.post(`${API_BASE_URL}/quality-analytics/datasets`, () =>
        HttpResponse.json({ report: IMPORT_REPORT_FIXTURE, dataset: null }, { status: 201 }),
      ),
    );
    const result = await createImportedDataset(new File(["y"], "f.csv"), mappingFromPreview(preview), 1000);
    expect(result.dataset).toBeNull();
    expect(result.report.rows_quarantined).toBe(5);
  });
});
