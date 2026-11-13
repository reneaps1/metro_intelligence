import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { renderAuthed } from "../../test/renderAuthed";
import { realQualityHandlers, server, VALID_EMAIL, VALID_PASSWORD } from "../../test/server";
import { QualityJoinPanel } from "./QualityJoinPanel";

const API = "http://localhost:8000/api/v1";
const login = { email: VALID_EMAIL, password: VALID_PASSWORD };

// Fictitious response: 4 buckets, mold temperature (quality-driven) or a control signal.
function joinFixture(signal: string) {
  const imposed = signal.endsWith("mold_temp");
  return {
    dataset: "real-dimensional",
    scenario_id: "real_calendar",
    generator_version: "process-sim-1.2.0",
    signal: { id: signal, name: imposed ? "Temperatura de molde" : "Presión de mantenimiento", unit: imposed ? "°C" : "bar" },
    target: "total",
    target_label: "NOK total",
    bucket_minutes: 30,
    lag_minutes: 0,
    utc_offset_minutes: -300,
    n: 4,
    pearson_r: imposed ? 0.91 : 0.02,
    slope: imposed ? 0.01 : 0.0001,
    intercept: 0.05,
    r_squared: imposed ? 0.83 : 0.0004,
    buckets: [0, 1, 2, 3].map((i) => ({ start_ts: 1_790_000_000 + i * 1800, x: 55 + i, y: 0.05 + i * 0.01, pieces: 900, cycles: 60 })),
    lag_scan: [{ lag_minutes: 0, r: imposed ? 0.91 : 0.02, n: 4 }],
    best_lag_minutes: 0,
    causal_imposed: imposed,
    provenance: ["REAL", "SIMULATED", "EXPERIMENTAL"],
    notes: [
      "Unión ilustrativa por tiempo: no hay trazabilidad ciclo → pieza.",
      imposed
        ? "La temperatura de molde simulada se construyó siguiendo la tasa de rechazo real: la relación está impuesta por construcción, no medida."
        : "Señal simulada sin vínculo con la calidad: sirve de control (se espera r cercano a 0).",
    ],
  };
}

describe("QualityJoinPanel (Vista A)", () => {
  it("explains that it needs the local REAL dataset", async () => {
    renderAuthed(<QualityJoinPanel />, login);
    expect(await screen.findByText(/Necesita el dataset REAL/)).toBeInTheDocument();
  });

  it("joins the REAL pieces with the simulated signal and labels the imposed relation", async () => {
    const seen: string[] = [];
    server.use(
      ...realQualityHandlers(),
      http.get(`${API}/quality-analytics/process-join`, ({ request }) => {
        const signal = new URL(request.url).searchParams.get("signal") ?? "";
        seen.push(signal);
        return HttpResponse.json(joinFixture(signal));
      }),
    );
    const user = userEvent.setup();
    renderAuthed(<QualityJoinPanel />, login);
    expect(await screen.findByText(/impuesta por construcción/)).toBeInTheDocument();
    expect(screen.getByText("0.91")).toBeInTheDocument();
    expect(seen[0]).toBe("L1.INY-01.mold_temp");

    await user.selectOptions(screen.getByLabelText("Señal simulada"), "holding_pressure");
    expect(await screen.findByText(/sirve de control/)).toBeInTheDocument();
    await waitFor(() => expect(seen.at(-1)).toBe("L1.INY-01.holding_pressure"));
  });
});
