import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { SignalCard } from "./SignalCard";
import type { ControlLimitsUpdatedEvent, PointEvent } from "../../lib/live-monitor/types";

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
  cpk: "1.42",
  center_line: "10.00",
  ucl: "10.10",
  lcl: "9.90",
  engine_name: "spc_engine",
  engine_version: "v1",
};

describe("SignalCard", () => {
  it("shows a waiting state before any point has arrived", () => {
    render(<SignalCard characteristicName="Bore Diameter A" partCode="MI-DEMO-1001" unit="mm" points={[]} controlLimits={null} />);

    expect(screen.getByText("Bore Diameter A")).toBeInTheDocument();
    expect(screen.getByText(/waiting for data/i)).toBeInTheDocument();
    expect(screen.getByText("--")).toBeInTheDocument();
  });

  it("shows the OK chip and last value once points have arrived", () => {
    render(
      <SignalCard
        characteristicName="Bore Diameter A"
        partCode="MI-DEMO-1001"
        unit="mm"
        points={[point({ value: "9.990" }), point({ value: "10.010" })]}
        controlLimits={null}
      />,
    );

    expect(screen.getByText("OK")).toBeInTheDocument();
    expect(screen.getByText("10.010 mm")).toBeInTheDocument();
  });

  it("shows the NOK chip for an out-of-tolerance point", () => {
    render(
      <SignalCard
        characteristicName="Bore Diameter A"
        partCode="MI-DEMO-1001"
        unit="mm"
        points={[point({ value: "11.500", is_ok: false })]}
        controlLimits={null}
      />,
    );

    expect(screen.getByText("NOK")).toBeInTheDocument();
  });

  it("shows the Cpk once a control-limits event has arrived", () => {
    render(
      <SignalCard
        characteristicName="Bore Diameter A"
        partCode="MI-DEMO-1001"
        unit="mm"
        points={[point()]}
        controlLimits={CONTROL_LIMITS}
      />,
    );

    expect(screen.getByText(/cpk 1\.42/i)).toBeInTheDocument();
    expect(screen.getByText(/spc_engine/)).toBeInTheDocument();
  });
});
