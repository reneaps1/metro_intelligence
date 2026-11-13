import { describe, expect, it } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { http, HttpResponse } from "msw";
import { renderAuthed } from "../../test/renderAuthed";
import { server, VALID_EMAIL, VALID_PASSWORD } from "../../test/server";
import { ProcessOverviewPage } from "./ProcessOverviewPage";
import { OperationDetailPage } from "./OperationDetailPage";
import { PieceTracePage } from "./PieceTracePage";
import type { LineOverview, Operation, OperationSummary, StepOverview } from "../../lib/process/types";

const API = "http://localhost:8000/api/v1";
const RANGE = { start: "2026-03-01", end: "2026-03-02", first_available: "2026-01-01", last_available: "2026-03-02" };

function op(sequence: number, code: string, name: string, kind: Operation["kind"], side: Operation["side"] = null): Operation {
  return { id: `op-${code}`, code, name, kind, side, sequence };
}

const OPERATIONS = [
  op(3, "LEN-CON", "Pin length connector", "pin_length", "connector"),
  op(1, "ET1", "Electrical test 1", "electrical"),
  op(7, "TYPE", "Type check", "type_check"),
];

function step(operation: Operation, overrides: Partial<StepOverview> = {}): StepOverview {
  return {
    operation,
    pieces: 1000,
    machine_nok: 0,
    machine_nok_rate: 0,
    spec_nok: 0,
    spec_nok_rate: null,
    first_pass_yield: 1,
    repeat_attempts: 0,
    has_specification: false,
    worst_cpk: null,
    disagreements: 0,
    coverage: 1,
    partial_logging: false,
    status: "ok",
    trend: [{ day: "2026-03-02", pieces: 1000, machine_nok: 0, spec_nok: 0 }],
    ...overrides,
  };
}

const OVERVIEW: LineOverview = {
  line: { id: "line-1", code: "MI-DEMO-LINE-01", name: "Demo line", operations: OPERATIONS },
  range: RANGE,
  recipes: [
    { id: "rec-2", code: 2, label: "Recipe 2 (variant pending)", variant_part_number: null, variant_pending: true },
    { id: "rec-3", code: 3, label: "MI-DEMO-2001-A", variant_part_number: "MI-DEMO-2001-A", variant_pending: false },
  ],
  selected_recipe_ids: [],
  reference_pieces: 1000,
  rolled_yield: 0.975,
  rolled_yield_steps: 2,
  steps: [
    step(OPERATIONS[0], { has_specification: true, spec_nok: 25, spec_nok_rate: 0.025, status: "critical", disagreements: 12, worst_cpk: 0.91 }),
    step(OPERATIONS[1], { pieces: 40, coverage: 0.04, partial_logging: true, machine_nok_rate: 0.6, status: "neutral" }),
    step(OPERATIONS[2]),
  ],
};

function overviewHandlers(onOverview?: (url: URL) => void) {
  return [
    http.get(`${API}/process/lines`, () => HttpResponse.json([OVERVIEW.line])),
    http.get(`${API}/process/lines/line-1/overview`, ({ request }) => {
      onOverview?.(new URL(request.url));
      return HttpResponse.json(OVERVIEW);
    }),
  ];
}

describe("ProcessOverviewPage", () => {
  it("shows the steps in line order with status, drawing NOK and partial coverage", async () => {
    server.use(...overviewHandlers());
    renderAuthed(<ProcessOverviewPage />, { email: VALID_EMAIL, password: VALID_PASSWORD, route: "/process" });

    const flow = await screen.findByRole("list", { name: "Process steps in order" });
    const names = within(flow)
      .getAllByRole("link")
      .map((link) => ["Electrical test 1", "Pin length connector", "Type check"].find((n) => link.textContent?.includes(n)));
    expect(names).toEqual(["Electrical test 1", "Pin length connector", "Type check"]);

    expect(within(flow).getByText("Action")).toBeInTheDocument();
    expect(screen.getAllByText("Action needed").length).toBeGreaterThan(0); // full text in the table
    expect(within(flow).getByText("Logs 4.0% of pieces")).toBeInTheDocument();
    expect(within(flow).getByText(/station OK, drawing NOK/)).toBeInTheDocument();
    // The electrical test logs 4 % of the pieces: it is a partial record, not a
    // quality status, and stays out of the line-level tiles.
    expect(within(flow).getByText("Partial log")).toBeInTheDocument();
    expect(screen.getByText("Rolled yield · 2 fully logged steps")).toBeInTheDocument();
    expect(screen.getByText("97.50%")).toBeInTheDocument();
    expect(screen.getByText("Worst step · Pin length connector")).toBeInTheDocument();
    expect(screen.getByText("2.50% NOK")).toBeInTheDocument();
    expect(screen.getByText(/Not drawn, because they log only part of the pieces: Electrical test 1\./)).toBeInTheDocument();
    // Every card shows the same three rows.
    expect(within(flow).getAllByText("1st pass")).toHaveLength(3);
    expect(within(flow).getByText("NOK per drawing")).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Results per process step" })).toBeInTheDocument();
    expect(screen.getAllByText("No spec").length).toBeGreaterThan(0);
  });

  it("says when a step has no data in the range and when it last had some", async () => {
    server.use(
      http.get(`${API}/process/lines`, () => HttpResponse.json([OVERVIEW.line])),
      http.get(`${API}/process/lines/line-1/overview`, () =>
        HttpResponse.json({
          ...OVERVIEW,
          steps: [step(OPERATIONS[0], { pieces: 0, coverage: 0, status: "neutral", trend: [], last_day: "2026-06-30" })],
        }),
      ),
    );
    renderAuthed(<ProcessOverviewPage />, { email: VALID_EMAIL, password: VALID_PASSWORD, route: "/process" });
    const flow = await screen.findByRole("list", { name: "Process steps in order" });
    expect(within(flow).getByText(/No data in this range/)).toBeInTheDocument();
    expect(within(flow).getByText("Jun 30, 2026")).toBeInTheDocument();
    expect(within(flow).queryByText(/Logs/)).not.toBeInTheDocument();
  });

  it("sends the recipe filter to the API and keeps it in the step links", async () => {
    const seen: string[] = [];
    server.use(...overviewHandlers((url) => seen.push(url.searchParams.getAll("recipe_id").join(","))));
    renderAuthed(
      <Routes>
        <Route path="/process" element={<ProcessOverviewPage />} />
      </Routes>,
      { email: VALID_EMAIL, password: VALID_PASSWORD, route: "/process" },
    );

    await screen.findByRole("list", { name: "Process steps in order" });
    await userEvent.selectOptions(screen.getByLabelText("Recipe"), "rec-3");
    await waitFor(() => expect(seen).toContain("rec-3"));
    const link = screen.getAllByRole("link", { name: /Pin length connector/ })[0];
    expect(link.getAttribute("href")).toContain("recipe=rec-3");
  });

  it("explains how to load data when no line exists yet", async () => {
    server.use(http.get(`${API}/process/lines`, () => HttpResponse.json([])));
    renderAuthed(<ProcessOverviewPage />, { email: VALID_EMAIL, password: VALID_PASSWORD, route: "/process" });
    expect(await screen.findByText("No line data yet")).toBeInTheDocument();
  });
});

const SUMMARY: OperationSummary = {
  operation: OPERATIONS[0],
  range: RANGE,
  recipes: OVERVIEW.recipes,
  pieces: 1000,
  machine_nok: 0,
  spec_nok: 25,
  repeat_attempts: 2,
  disagreements: 12,
  coverage: 1,
  partial_logging: false,
  status: "critical",
  characteristics: [
    {
      id: "char-ref",
      code: "LEN-CON-REF",
      name: "Reference",
      unit: "mm",
      n: 1000,
      mean: 0.01,
      std_dev: 0.02,
      min: -0.05,
      max: 0.06,
      machine_nok: 0,
      spec_nok: 0,
      machine_ok_spec_nok: 0,
      gross: 0,
      specification: null,
      cp: null,
      cpk: null,
      capability_kind: null,
    },
    {
      id: "char-p1",
      code: "LEN-CON-P1",
      name: "Pin 1 length",
      unit: "mm",
      n: 1000,
      mean: 5.45,
      std_dev: 0.03,
      min: 5.3,
      max: 5.9,
      machine_nok: 0,
      spec_nok: 25,
      machine_ok_spec_nok: 12,
      gross: 3,
      specification: { nominal: "5.5", lower_tol: "-0.3", upper_tol: "0.3", lower_limit: "5.2", upper_limit: "5.8" },
      cp: 3.3,
      cpk: 0.91,
      capability_kind: "Cpk",
    },
  ],
  by_recipe: [{ key: "rec-2", label: "Recipe 2 (variant pending)", pieces: 1000, machine_nok: 0, spec_nok: 25 }],
  by_nest: [
    { key: "1", label: "Nest 1", pieces: 600, machine_nok: 0, spec_nok: 3 },
    { key: "2", label: "Nest 2", pieces: 400, machine_nok: 0, spec_nok: 22 },
  ],
  trend: [{ day: "2026-03-02", pieces: 1000, machine_nok: 0, spec_nok: 25 }],
};

describe("OperationDetailPage", () => {
  it("lists characteristics, shows the station-vs-drawing finding and opens a characteristic", async () => {
    server.use(
      http.get(`${API}/process/operations/op-LEN-CON/summary`, () => HttpResponse.json(SUMMARY)),
      http.get(`${API}/process/operations/op-LEN-CON/characteristics/:cid`, ({ params }) =>
        HttpResponse.json({
          characteristic: SUMMARY.characteristics.find((c) => c.id === params.cid),
          range: RANGE,
          bins: [
            { lower: 5.3, upper: 5.5, count: 900 },
            { lower: 5.8, upper: 6.0, count: 25 },
          ],
          below_range: 0,
          above_range: 3,
          daily: [{ day: "2026-03-02", n: 1000, mean: 5.45, min: 5.3, max: 5.9, spec_nok: 25, machine_nok: 0, cpk: 0.91 }],
        }),
      ),
    );
    renderAuthed(
      <Routes>
        <Route path="/process/operations/:operationId" element={<OperationDetailPage />} />
      </Routes>,
      { email: VALID_EMAIL, password: VALID_PASSWORD, route: "/process/operations/op-LEN-CON" },
    );

    expect(await screen.findByRole("heading", { name: "Pin length connector" })).toBeInTheDocument();
    expect(screen.getByText(/12 values passed the station but are outside the drawing tolerance/)).toBeInTheDocument();
    expect(screen.getByText("No specification")).toBeInTheDocument();
    expect(screen.getByText("5.200 – 5.800 mm")).toBeInTheDocument();
    expect(screen.getByText("Cpk 0.91")).toBeInTheDocument();
    // Tiles: one number each, the count goes in the label.
    expect(screen.getByText("Out of drawing · 25 pieces")).toBeInTheDocument();
    expect(screen.getByText("2.50%")).toBeInTheDocument();
    // Gross readings are named where they were left out.
    expect(screen.getByText("excl. 3 gross")).toBeInTheDocument();
    expect(screen.getByText(/leave out gross readings/)).toBeInTheDocument();
    // Breakdown: worst nest first, its bar full width.
    const nestRows = within(screen.getByRole("table", { name: "By nest" })).getAllByRole("row").slice(1);
    expect(nestRows[0]).toHaveTextContent("Nest 2");
    expect(nestRows[0]).toHaveTextContent("22 · 5.50%");
    expect(nestRows[1]).toHaveTextContent("Nest 1");
    // The first characteristic with a specification opens by default.
    expect(await screen.findByRole("heading", { name: "Pin 1 length · LEN-CON-P1" })).toBeInTheDocument();
    expect(await screen.findByText(/3 above the shown range/)).toBeInTheDocument();
  });
});

describe("OperationDetailPage recipe filter", () => {
  it("shows the recipe chosen on the overview and lets the user change it on the step page", async () => {
    const seen: string[] = [];
    server.use(
      http.get(`${API}/process/operations/op-LEN-CON/summary`, ({ request }) => {
        seen.push(new URL(request.url).searchParams.getAll("recipe_id").join(","));
        return HttpResponse.json(SUMMARY);
      }),
      http.get(`${API}/process/operations/op-LEN-CON/characteristics/:cid`, () =>
        HttpResponse.json({ detail: "none" }, { status: 404 }),
      ),
    );
    renderAuthed(
      <Routes>
        <Route path="/process/operations/:operationId" element={<OperationDetailPage />} />
      </Routes>,
      { email: VALID_EMAIL, password: VALID_PASSWORD, route: "/process/operations/op-LEN-CON?recipe=rec-3" },
    );

    const select = (await screen.findByLabelText("Recipe")) as HTMLSelectElement;
    expect(within(select).getAllByRole("option").map((o) => o.textContent)).toEqual([
      "All recipes",
      "Recipe 2 (variant pending)",
      "MI-DEMO-2001-A",
    ]);
    expect(select.value).toBe("rec-3");
    expect(seen).toContain("rec-3");

    await userEvent.selectOptions(select, "rec-2");
    await waitFor(() => expect(seen).toContain("rec-2"));
    await userEvent.selectOptions(screen.getByLabelText("Recipe"), "");
    await waitFor(() => expect(seen[seen.length - 1]).toBe(""));
  });
});

describe("PieceTracePage", () => {
  it("shows each step with the station and drawing verdicts", async () => {
    server.use(
      http.get(`${API}/process/pieces/900002`, () =>
        HttpResponse.json({
          serial_number: "900002",
          line: OVERVIEW.line,
          recipe: OVERVIEW.recipes[0],
          first_seen_at: "2026-03-02T06:00:00Z",
          steps: [
            {
              operation: OPERATIONS[0],
              attempt: 1,
              recorded_at: "2026-03-02T06:00:01Z",
              nest: 1,
              program_number: null,
              machine_ok: true,
              values: [
                {
                  characteristic_id: "char-p1",
                  code: "LEN-CON-P1",
                  name: "Pin 1 length",
                  unit: "mm",
                  value: "5.950000000",
                  machine_ok: true,
                  is_ok: false,
                  deviation: "0.450000000",
                  specification: SUMMARY.characteristics[1].specification,
                },
              ],
            },
          ],
        }),
      ),
    );
    renderAuthed(
      <Routes>
        <Route path="/process/pieces/:serial" element={<PieceTracePage />} />
      </Routes>,
      { email: VALID_EMAIL, password: VALID_PASSWORD, route: "/process/pieces/900002" },
    );

    expect(await screen.findByText("Recipe 2 (variant pending)")).toBeInTheDocument();
    const table = screen.getByRole("table", { name: "Values measured at Pin length connector" });
    expect(within(table).getByText("5.9500 mm")).toBeInTheDocument();
    expect(within(table).getByText("OK")).toBeInTheDocument();
    expect(within(table).getByText("NOK")).toBeInTheDocument();
  });

  it("says when a piece is not in the loaded data", async () => {
    server.use(
      http.get(`${API}/process/pieces/123`, () => HttpResponse.json({ detail: "Piece not found." }, { status: 404 })),
    );
    renderAuthed(
      <Routes>
        <Route path="/process/pieces/:serial" element={<PieceTracePage />} />
      </Routes>,
      { email: VALID_EMAIL, password: VALID_PASSWORD, route: "/process/pieces/123" },
    );
    expect(await screen.findByText("No piece 123 in the loaded data.")).toBeInTheDocument();
  });
});

describe("PositionMapCard", () => {
  it("shows the density map, the tolerance and the nests ranked by share out of tolerance", async () => {
    const posCon = op(6, "POS-CON", "Pin position connector", "pin_position", "connector");
    const xChar = { ...SUMMARY.characteristics[1], id: "char-x", code: "POS-CON-P1X", name: "Pin 1 X deviation", specification: null, cpk: null, cp: null, capability_kind: null };
    const pins: number[] = [];
    server.use(
      http.get(`${API}/process/operations/op-POS-CON/summary`, () =>
        HttpResponse.json({ ...SUMMARY, operation: posCon, characteristics: [xChar] }),
      ),
      http.get(`${API}/process/operations/op-POS-CON/characteristics/:cid`, () => HttpResponse.json({ detail: "none" }, { status: 404 })),
      http.get(`${API}/process/operations/op-POS-CON/position-map`, ({ request }) => {
        const pin = Number(new URL(request.url).searchParams.get("pin") ?? 1);
        pins.push(pin);
        const stats = { out_x: 1, out_y: 30, out_radial: 12, machine_nok: 2, median_x: 0.07, median_y: 0.12, p95_x: 0.17, p95_y: 0.27 };
        return HttpResponse.json({
          operation: posCon,
          range: RANGE,
          pin,
          pins: [1, 2],
          unit: "mm",
          tolerance_x: 0.3,
          tolerance_y: 0.3,
          extent: 0.6,
          bins: 40,
          cells: [
            { ix: 4, iy: 8, count: 900 },
            { ix: 30, iy: 32, count: 3 },
          ],
          beyond_extent: 5,
          points: [
            { x: 0.08, y: 0.1, nest: 1 },
            { x: 0.3, y: 0.25, nest: 9 },
          ],
          sampled_from: 903,
          total: { pieces: 1000, out_of_tolerance: 31, ...stats },
          nests: [
            { nest: 1, pieces: 600, out_of_tolerance: 1, ...stats },
            { nest: 9, pieces: 400, out_of_tolerance: 30, ...stats, median_y: 0.22 },
          ],
        });
      }),
    );
    renderAuthed(
      <Routes>
        <Route path="/process/operations/:operationId" element={<OperationDetailPage />} />
      </Routes>,
      { email: VALID_EMAIL, password: VALID_PASSWORD, route: "/process/operations/op-POS-CON" },
    );

    expect(await screen.findByRole("heading", { name: "Pin position map · |ΔX| vs |ΔY|" })).toBeInTheDocument();
    expect(await screen.findByRole("img", { name: /Point cloud of pin 1 position deviations; 1,000 pieces/ })).toBeInTheDocument();
    expect(screen.getByText("Outside the circle (r 0.30)")).toBeInTheDocument();
    expect(screen.getByText(/2 pins sampled at random from 903/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Density" }));
    expect(screen.getByRole("img", { name: /Density of pin 1/ })).toBeInTheDocument();
    expect(screen.getByText("96.90%")).toBeInTheDocument(); // inside tolerance
    expect(screen.getByText("Drawing tolerance 0.30")).toBeInTheDocument();
    const nestRows = within(screen.getByRole("table", { name: /Pin position by nest/ })).getAllByRole("row").slice(1);
    expect(nestRows[0]).toHaveTextContent("N9"); // highest share out of tolerance first
    expect(nestRows[0]).toHaveTextContent("30 · 7.50%");

    await userEvent.click(screen.getByRole("button", { name: "Pin 2" }));
    await waitFor(() => expect(pins).toContain(2));
  });
});
