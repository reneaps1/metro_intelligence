import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { SignalDetailPanel } from "./SignalDetailPanel";
import type { ControlLimitsUpdatedEvent, PointEvent } from "../../lib/live-monitor/types";
import type { Specification } from "../../lib/catalog/types";

const SPEC: Specification = {
  id: "spec-1",
  characteristic_id: "char-1",
  nominal: "10.000",
  lower_tol: "-0.050",
  upper_tol: "0.050",
  unit: "mm",
  valid_from: "2026-01-01T00:00:00Z",
  valid_to: null,
  created_at: "2026-01-01T00:00:00Z",
};

function point(overrides: Partial<PointEvent> = {}): PointEvent {
  return {
    type: "point",
    characteristic_id: "char-1",
    value: "10.010",
    deviation: "0.010",
    is_ok: true,
    measured_at: "2026-01-01T00:00:00Z",
    rationale: "Within tolerance (+0.010 mm from nominal).",
    engine_name: "compliance_engine",
    engine_version: "v1",
    ...overrides,
  };
}

const CONTROL_LIMITS: ControlLimitsUpdatedEvent = {
  type: "control_limits_updated",
  characteristic_id: "char-1",
  cpk: "0.91",
  center_line: "10.005",
  ucl: "10.045",
  lcl: "9.965",
  engine_name: "spc_engine",
  engine_version: "v1",
};

function renderPanel(props: Partial<Parameters<typeof SignalDetailPanel>[0]> = {}) {
  return render(
    <MemoryRouter>
      <SignalDetailPanel
        characteristicId="char-1"
        unit="mm"
        specification={SPEC}
        points={[]}
        controlLimits={null}
        {...props}
      />
    </MemoryRouter>,
  );
}

describe("SignalDetailPanel", () => {
  it("shows a waiting message before there are enough points to plot", () => {
    renderPanel({ points: [point()] });

    expect(screen.getByText(/waiting for enough replayed points/i)).toBeInTheDocument();
  });

  it("shows the compliance rationale with engine attribution once points arrive", () => {
    const rationale = "0.150 mm above the upper tolerance limit (deviation +0.150 mm, limit +0.050 mm).";
    renderPanel({
      points: [point({ value: "9.990", deviation: "-0.010" }), point({ value: "10.150", deviation: "0.150", is_ok: false, rationale })],
    });

    expect(screen.getByText(rationale)).toBeInTheDocument();
    expect(screen.getByText(/compliance_engine/)).toBeInTheDocument();
  });

  it("phrases the real Cpk value with the standard 1.33 capability threshold, never inventing a new number", () => {
    renderPanel({
      points: [point({ value: "9.990" }), point({ value: "10.010" })],
      controlLimits: CONTROL_LIMITS,
    });

    expect(screen.getByText(/cpk 0\.91/i)).toBeInTheDocument();
    expect(screen.getByText(/below the 1\.33 capability threshold/i)).toBeInTheDocument();
    expect(screen.getByText(/spc_engine/)).toBeInTheDocument();
  });

  it("reports Cpk as undefined without hiding the control limits, when the engine returns null", () => {
    renderPanel({
      points: [point({ value: "10.0" }), point({ value: "10.0" })],
      controlLimits: { ...CONTROL_LIMITS, cpk: null },
    });

    expect(screen.getByText(/cpk is undefined/i)).toBeInTheDocument();
  });

  it("links to the full-detail destination for this characteristic", () => {
    renderPanel({ points: [point(), point()] });

    expect(screen.getByRole("link", { name: /view full detail/i })).toHaveAttribute(
      "href",
      "/live-monitor/char-1",
    );
  });
});
