import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LiveMonitorControls } from "./LiveMonitorControls";

function renderControls(overrides: Partial<Parameters<typeof LiveMonitorControls>[0]> = {}) {
  const onTogglePause = vi.fn();
  const onChangeSpeed = vi.fn();
  const onChangeScenario = vi.fn();
  render(
    <LiveMonitorControls
      paused={false}
      onTogglePause={onTogglePause}
      speedMultiplier={1}
      onChangeSpeed={onChangeSpeed}
      scenario={null}
      onChangeScenario={onChangeScenario}
      disabled={false}
      {...overrides}
    />,
  );
  return { onTogglePause, onChangeSpeed, onChangeScenario };
}

describe("LiveMonitorControls", () => {
  it("shows Pause when playing and calls onTogglePause when clicked", async () => {
    const user = userEvent.setup();
    const { onTogglePause } = renderControls({ paused: false });

    const button = screen.getByRole("button", { name: /pause/i });
    await user.click(button);

    expect(onTogglePause).toHaveBeenCalledTimes(1);
  });

  it("shows Play when paused", () => {
    renderControls({ paused: true });
    expect(screen.getByRole("button", { name: /play/i })).toBeInTheDocument();
  });

  it("calls onChangeSpeed with a numeric value when the speed select changes", async () => {
    const user = userEvent.setup();
    const { onChangeSpeed } = renderControls();

    await user.selectOptions(screen.getByLabelText(/playback speed/i), "5");

    expect(onChangeSpeed).toHaveBeenCalledWith(5);
  });

  it("calls onChangeScenario with the scenario name, or null for the default mix", async () => {
    const user = userEvent.setup();
    const { onChangeScenario } = renderControls();

    await user.selectOptions(screen.getByLabelText(/scenario/i), "high_variance");
    expect(onChangeScenario).toHaveBeenCalledWith("high_variance");

    await user.selectOptions(screen.getByLabelText(/scenario/i), "Default mix");
    expect(onChangeScenario).toHaveBeenCalledWith(null);
  });

  it("disables the pause button and speed select when disabled", () => {
    renderControls({ disabled: true });
    expect(screen.getByRole("button", { name: /pause/i })).toBeDisabled();
    expect(screen.getByLabelText(/playback speed/i)).toBeDisabled();
  });
});
