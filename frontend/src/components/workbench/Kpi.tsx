import clsx from "clsx";

// IQ-F16: KPI tile of the industrial workbench (design-system.md §4.3), the
// line panel's tile at desktop size. The figure is neutral; `tone="nok"` gives
// it the muted NOK accent (NOK pieces and rates), and the alarm red only
// appears when `alarm` says a limit asks for action. Styles live in
// features/demo/workbench/workbench.css (scoped to .wb-root).

const UNIT = /^(.*\d)(\s?)(%|×)$/;

export function Kpi({
  label,
  value,
  hint,
  tone,
  alarm = false,
  size = "md",
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "nok";
  alarm?: boolean;
  size?: "md" | "sm";
}) {
  // A trailing unit is set smaller, like the panel ("9.33 %" -> 9.33 + small %).
  const unit = UNIT.exec(value);
  return (
    <div className={clsx("wb-kpi", tone, alarm && "alarm", size === "sm" && "sm")}>
      <p className="wb-label">{label}</p>
      <p className="wb-kpi-v">
        {unit ? (
          <>
            {/* Screen readers (and text queries) get the value as written; the eye gets the small unit. */}
            <span className="sr-only">{value}</span>
            <span aria-hidden="true">
              {unit[1]}
              <small>
                {unit[2]}
                {unit[3]}
              </small>
            </span>
          </>
        ) : (
          value
        )}
      </p>
      {hint && <p className="wb-kpi-f">{hint}</p>}
    </div>
  );
}
