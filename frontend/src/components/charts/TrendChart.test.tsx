import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { TrendChart, type ControlLimits } from "./TrendChart";
import type { MeasurementPoint, Specification } from "../../lib/mock/types";

const SPEC: Specification = { nominal: 10, lowerTol: -0.05, upperTol: 0.05, unit: "mm" };

const CONTROL_LIMITS: ControlLimits = { centerLine: 0.005, ucl: 0.045, lcl: -0.035 };

function points(count: number): MeasurementPoint[] {
  return Array.from({ length: count }, (_, i) => ({
    measuredAt: new Date(2026, 0, i + 1).toISOString(),
    value: 10 + i * 0.001,
    deviation: i * 0.001,
    isOk: true,
    sampleIndex: i,
  }));
}

// Recharts' <ResponsiveContainer> only lays out its chart children once it
// can measure a real container size (see ResponsiveContainer's initial
// `getBoundingClientRect()` call) -- jsdom never performs real layout, so
// every element reports a 0x0 rect unless stubbed. Recharts' own mouse
// handlers then convert `event.pageX` into a chart-relative x using that
// same rect, so `pageX` has to be supplied explicitly (jsdom's MouseEvent
// does not derive it from `clientX` the way real browsers do).
beforeEach(() => {
  vi.spyOn(Element.prototype, "getBoundingClientRect").mockReturnValue({
    width: 400,
    height: 280,
    top: 0,
    left: 0,
    right: 400,
    bottom: 280,
    x: 0,
    y: 0,
    toJSON: () => {},
  });
  // Recharts also divides its bounding-rect width by `offsetWidth` to
  // compute a hit-test scale factor -- jsdom's offsetWidth/offsetHeight are
  // always 0 (no real layout), which would make that scale Infinity and
  // silently break every mouse-to-data-index lookup.
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(400);
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(280);
});

afterEach(() => {
  vi.restoreAllMocks();
});

function dotCenters(container: HTMLElement): number[] {
  return Array.from(container.querySelectorAll<SVGCircleElement>("svg circle[r='3']")).map((el) =>
    Number(el.getAttribute("cx")),
  );
}

describe("TrendChart", () => {
  it("without zoomable, renders no zoom-out affordance and no crosshair cursor", () => {
    const { container } = render(<TrendChart points={points(5)} specification={SPEC} unit="mm" />);

    expect(screen.queryByRole("button", { name: /zoom out/i })).not.toBeInTheDocument();
    const wrapper = container.querySelector(".recharts-wrapper") as HTMLElement | null;
    expect(wrapper?.style.cursor).not.toBe("crosshair");
  });

  it("zoomable renders a crosshair cursor for the drag affordance", () => {
    const { container } = render(<TrendChart points={points(5)} specification={SPEC} unit="mm" zoomable />);

    const wrapper = container.querySelector(".recharts-wrapper") as HTMLElement | null;
    expect(wrapper?.style.cursor).toBe("crosshair");
  });

  it("dragging across two or more points commits a zoom, and Zoom Out clears it", () => {
    const { container } = render(<TrendChart points={points(5)} specification={SPEC} unit="mm" zoomable />);

    const centers = dotCenters(container);
    expect(centers.length).toBe(5);
    const chart = container.querySelector(".recharts-surface") as SVGSVGElement;

    fireEvent.mouseDown(chart, { clientX: centers[0], clientY: 100, pageX: centers[0], pageY: 100 });
    fireEvent.mouseMove(chart, { clientX: centers[2], clientY: 100, pageX: centers[2], pageY: 100 });
    fireEvent.mouseUp(chart, { clientX: centers[2], clientY: 100, pageX: centers[2], pageY: 100 });

    expect(screen.getByRole("button", { name: /zoom out/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /zoom out/i }));
    expect(screen.queryByRole("button", { name: /zoom out/i })).not.toBeInTheDocument();
  });

  it("a drag that doesn't move (a click) does not commit a zoom", () => {
    const { container } = render(<TrendChart points={points(5)} specification={SPEC} unit="mm" zoomable />);

    const centers = dotCenters(container);
    const chart = container.querySelector(".recharts-surface") as SVGSVGElement;

    fireEvent.mouseDown(chart, { clientX: centers[0], clientY: 100, pageX: centers[0], pageY: 100 });
    fireEvent.mouseUp(chart, { clientX: centers[0], clientY: 100, pageX: centers[0], pageY: 100 });

    expect(screen.queryByRole("button", { name: /zoom out/i })).not.toBeInTheDocument();
  });

  it("without controlLimits, there is no CL explanation to show", () => {
    render(<TrendChart points={points(5)} specification={SPEC} unit="mm" />);

    expect(screen.queryByRole("button", { name: /what is cl/i })).not.toBeInTheDocument();
  });

  it("with controlLimits, explains CL via a keyboard-reachable tooltip", () => {
    render(<TrendChart points={points(5)} specification={SPEC} unit="mm" controlLimits={CONTROL_LIMITS} />);

    const trigger = screen.getByRole("button", { name: /what is cl/i });
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();

    fireEvent.focus(trigger);
    expect(screen.getByRole("tooltip")).toHaveTextContent(/center line/i);

    fireEvent.keyDown(trigger, { key: "Escape" });
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });
});
