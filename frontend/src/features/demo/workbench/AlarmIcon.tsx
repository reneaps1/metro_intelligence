import clsx from "clsx";
import type { AlarmPriority } from "../../../lib/demo/alarms";

// ISA-101 alarm symbol: priority is coded by shape (diamond = 1, triangle = 2)
// as well as color, with a dark outline so it reads on any background.
// Blinks only while unacknowledged; reduced motion stops it (index.css).
export function AlarmIcon({
  priority,
  size = 16,
  blinking = false,
}: {
  priority: AlarmPriority;
  size?: number;
  blinking?: boolean;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      aria-hidden="true"
      className={clsx("flex-none", blinking && "wb-blink")}
    >
      {priority === 1 ? (
        <path d="M12 2 22 12 12 22 2 12z" className="fill-status-nok" stroke="#15191e" strokeWidth={1.5} />
      ) : (
        <path
          d="M12 2.5 22.5 21h-21z"
          className="fill-status-warning"
          stroke="#15191e"
          strokeWidth={1.5}
          strokeLinejoin="round"
        />
      )}
    </svg>
  );
}
