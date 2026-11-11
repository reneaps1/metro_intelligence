import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import {
  METROLOGIST_EMAIL,
  METROLOGIST_PASSWORD,
  server,
} from "../../../test/server";
import { renderAuthed } from "../../../test/renderAuthed";
import { DemoSessionProvider } from "../../../lib/demo/DemoSessionProvider";
import { PartControl } from "./PartControl";

const API = "http://localhost:8000/api/v1";
const CREDS = { email: METROLOGIST_EMAIL, password: METROLOGIST_PASSWORD };

const entry = (over: Record<string, unknown>) => ({
  label: "Pieza",
  line: "Línea demo B",
  description: "",
  source_type: "REAL",
  pieces: 1000,
  period_start: null,
  period_end: null,
  loaded: false,
  product: null,
  ...over,
});

describe("PartControl (IQ-F22/F28)", () => {
  it("lists parts by line with their drawing and tolerance status", async () => {
    server.use(
      http.get(`${API}/quality-analytics/catalog`, () =>
        HttpResponse.json({
          items: [
            entry({
              id: "real-a",
              label: "Programa demo · Conector demo (MI-DEMO-0042)",
              product: {
                name: "Conector demo",
                part_number: "MI-DEMO-0042",
                drawing: "MI-DEMO-DWG-7 rev B",
                customer_program: "Programa demo",
                characteristics_with_limits: 12,
              },
            }),
            entry({ id: "real-b", label: "Otra pieza" }),
          ],
          omitted: 0,
          initial_id: "real-a",
        }),
      ),
    );
    const user = userEvent.setup();
    renderAuthed(
      <DemoSessionProvider>
        <PartControl />
      </DemoSessionProvider>,
      CREDS,
    );
    await user.click(await screen.findByRole("button", { name: /Pieza/ }));
    expect(
      await screen.findByText("Programa demo · Conector demo (MI-DEMO-0042)"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /Plano MI-DEMO-DWG-7 rev B · 12 características con tolerancia/,
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Línea demo B")).toBeInTheDocument();
    expect(screen.getAllByRole("radio")).toHaveLength(2);
  });
});
