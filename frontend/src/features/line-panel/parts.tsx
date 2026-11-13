import clsx from "clsx";
import type { ReactNode } from "react";
import {
  actionOptions,
  currentStep,
  fmtInt,
  piecesToContain,
  plantClock,
  streakAt,
  streakPieces,
  whatText,
  whereText,
  type ActiveAlarm,
  type Kpis,
  type PanelSession,
  type ShiftCounts,
} from "../../lib/line-panel/model";
import { ESCALATION_S } from "../../lib/line-panel/model";
import type { LineAlarmEvent, LinePriority, LineReplay } from "../../lib/line-panel/types";

/** Everything a view needs at the replay cursor. */
export interface PanelView {
  r: LineReplay;
  idx: number;
  counts: ShiftCounts;
  k: Kpis;
  alarms: ActiveAlarm[];
  session: PanelSession;
  onAction: (alarm: LineAlarmEvent, option: number) => void;
}

const mmss = (s: number) => {
  const d = Math.max(0, Math.floor(s));
  return `${String(Math.floor(d / 60)).padStart(2, "0")}:${String(d % 60).padStart(2, "0")}`;
};

/**
 * ISA-101 priority symbol: diamond = 1 (stop), triangle = 2, square = advisory.
 * `onFill` inverts it for the solid alarm bands. Blinks only while unacknowledged.
 */
export function LpSymbol({
  priority,
  size = 24,
  onFill = false,
  blinking = false,
}: {
  priority: LinePriority;
  size?: number;
  onFill?: boolean;
  blinking?: boolean;
}) {
  const cls = clsx("flex-none", blinking && "wb-blink");
  if (priority === 3) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" aria-label="Aviso" role="img" className={cls}>
        <rect x="2.5" y="2.5" width="19" height="19" rx="2" fill="none" stroke="currentColor" strokeWidth={2.4} />
        <path d="M12 10.5v6.5M12 7v.4" stroke="currentColor" strokeWidth={2.6} strokeLinecap="round" />
      </svg>
    );
  }
  if (priority === 1) {
    const fill = onFill ? "var(--lp-p1-on)" : "var(--lp-p1-fill)";
    const mark = onFill ? "var(--lp-p1-fill)" : "var(--lp-p1-on)";
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" aria-label="Prioridad 1" role="img" className={cls}>
        <path d="M12 1 23 12 12 23 1 12Z" fill={fill} />
        <path d="M12 6.8v6.4M12 16.6v.4" stroke={mark} strokeWidth={2.6} strokeLinecap="round" />
      </svg>
    );
  }
  const fill = onFill ? "var(--lp-p2-on)" : "var(--lp-p2-fill)";
  const mark = onFill ? "var(--lp-p2-fill)" : "var(--lp-p2-on)";
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-label="Prioridad 2" role="img" className={cls}>
      <path d="M12 1.8 23.2 21.6H.8Z" fill={fill} strokeLinejoin="round" />
      <path d="M12 8.6v6M12 17.8v.4" stroke={mark} strokeWidth={2.6} strokeLinecap="round" />
    </svg>
  );
}

export function StripLegend() {
  return (
    <span className="lp-legend">
      <span>
        <i className="lp-sw" style={{ background: "var(--lp-piece-ok)" }} />
        OK
      </span>
      <span>
        <i className="lp-sw" style={{ background: "var(--lp-piece-nok)" }} />
        NOK
      </span>
      <span>
        <i className="lp-sw" style={{ background: "var(--lp-p1-fill)" }} />
        NOK en racha de paro
      </span>
    </span>
  );
}

/** Last `count` pieces up to the cursor (newest on the right); optionally only one nest. */
export function PieceStrip({
  r,
  idx,
  count,
  height,
  labels = false,
  nest,
}: {
  r: LineReplay;
  idx: number;
  count: number;
  height: number;
  labels?: boolean;
  nest?: number;
}) {
  const hot = streakPieces(r, idx);
  const cells: number[] = [];
  for (let i = idx; i >= 0 && cells.length < count; i--) {
    if (nest === undefined || r.pieces.nest[i] === nest) cells.push(i);
  }
  cells.reverse();
  return (
    <div className="lp-strip" style={{ height }} role="img" aria-label={`Últimas ${cells.length} piezas`}>
      {cells.map((i) => {
        const bad = r.pieces.nok[i] === 1;
        return (
          <div key={i} className={clsx("lp-cell", bad && (hot.has(i) ? "hot" : "nok"))}>
            {labels && bad && r.pieces.nest[i] != null && <span className="nl">{r.pieces.nest[i]}</span>}
          </div>
        );
      })}
    </div>
  );
}

/** Streak meter: segments up to the R1 limit; holds the full streak while an R1 alarm is open. */
export function StreakMeter({
  r,
  idx,
  alarms,
  scale = 1,
  stacked = false,
}: {
  r: LineReplay;
  idx: number;
  alarms: ActiveAlarm[];
  scale?: number;
  stacked?: boolean;
}) {
  const limit = r.rules.run_limit;
  const latched = alarms.find((a) => a.ev.rule === "R1");
  const cur = streakAt(r, idx);
  const shown = latched ? Math.max(cur, latched.ev.nests.length || limit) : cur;
  const run = Math.min(shown, limit);
  const on = run >= limit;
  return (
    <div className={clsx("lp-racha", stacked && "stacked")}>
      <div className="lp-segs">
        {Array.from({ length: limit }, (_, i) => (
          <div
            key={i}
            className={clsx("lp-seg", i < run ? (on ? "hot" : "on") : i === limit - 1 && "lim")}
            style={{ width: 56 * scale, height: 40 * scale }}
          />
        ))}
      </div>
      <div style={{ whiteSpace: "nowrap" }}>
        <div className="lp-num" style={{ fontSize: 34 * scale, fontWeight: 600, lineHeight: 1 }}>
          {shown} <span className="lp-muted" style={{ fontSize: "0.6em" }}>/ {limit}</span>
        </div>
        <div className="lp-muted" style={{ fontSize: 16 * scale, marginTop: 4 }}>
          {on ? "límite alcanzado → parar línea" : run === 0 ? "sin racha" : `a ${limit - run} pzs del paro`}
        </div>
      </div>
    </div>
  );
}

export function StepList({ items, done, size }: { items: string[]; done: boolean[]; size: number }) {
  const cur = currentStep(done);
  return (
    <ol className="lp-steps">
      {items.map((s, i) => (
        <li
          key={i}
          className={clsx("lp-step", done[i] ? "done" : i === cur && "cur")}
          style={{ fontSize: size }}
          aria-current={!done[i] && i === cur ? "step" : undefined}
        >
          <span className="n">{done[i] ? "✓" : i + 1}</span>
          <span>{s}</span>
        </li>
      ))}
    </ol>
  );
}

export function escalationLeft(a: ActiveAlarm): number {
  return (a.ev.priority === 1 ? ESCALATION_S[1] : ESCALATION_S[2]) - a.elapsed;
}

/** Unacknowledged: time without response + escalation countdown. Acknowledged: step and time since. */
export function AlarmTimer({ a, r, idx }: { a: ActiveAlarm; r: LineReplay; idx: number }) {
  if (!a.acked) {
    return (
      <div className="lp-timer">
        <div className="lbl">Sin reconocer</div>
        <div className="big">{mmss(a.elapsed)}</div>
        <div className="escl">
          {a.escalated ? (
            <b>Escalada a supervisor</b>
          ) : (
            <>
              Escala a supervisor en <b className="lp-num">{mmss(escalationLeft(a))}</b>
            </>
          )}
        </div>
      </div>
    );
  }
  return (
    <div className="lp-timer">
      <div className="lbl">Reconocida · paso {currentStep(a.done) + 1} de 4</div>
      <div className="big">{mmss(a.elapsed)}</div>
      <div className="escl">
        desde la alarma
        {a.ev.rule === "R1" && (
          <>
            {" "}
            · <b className="lp-num">{fmtInt(piecesToContain(a.ev, idx))}</b> pzs desde{" "}
            {plantClock(a.ev.evidence_from_ts, r.utc_offset_minutes)}
          </>
        )}
      </div>
    </div>
  );
}

/** Horizontal bullet: value bar, solid marker at the reference, dashed at the alarm limit. */
export function Bullet({ value, max, reference, limit }: { value: number | null; max: number; reference: number; limit: number }) {
  const v = value ?? 0;
  return (
    <div className="lp-bullet" aria-hidden="true">
      <div className={clsx("fill", v >= limit && "p2")} style={{ width: `${Math.min(100, (100 * v) / max)}%` }} />
      <div className="mk" style={{ left: `${(100 * reference) / max}%` }} />
      <div className="mk lim" style={{ left: `${(100 * limit) / max}%` }} />
    </div>
  );
}

export function Panel({
  title,
  aside,
  children,
  className,
  style,
}: {
  title: ReactNode;
  aside?: ReactNode;
  children: ReactNode;
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <section className={clsx("lp-panel", className)} style={style}>
      <div className="lp-ph">
        {title}
        {aside && <span className="aside">{aside}</span>}
      </div>
      {children}
    </section>
  );
}

export function ActionDialog({
  view,
  alarm,
  onClose,
}: {
  view: PanelView;
  alarm: ActiveAlarm;
  onClose: () => void;
}) {
  const { r, idx, onAction } = view;
  const ev = alarm.ev;
  return (
    <div className="lp-scrim">
      <div className="lp-dlg" role="dialog" aria-modal="true" aria-label="Registrar acción">
        <div className="lp-dlg-h">
          <LpSymbol priority={ev.priority} size={40} />
          Registrar acción · {ev.rule}
        </div>
        <div className="lp-dlg-sub">
          {whatText(r, ev, idx)} · {whereText(r, ev)}
        </div>
        {actionOptions(r, ev, idx).map((o, i) => (
          <button
            key={o.label}
            type="button"
            className="lp-opt"
            onClick={() => {
              onAction(ev, i);
              onClose();
            }}
          >
            <kbd>{i + 1}</kbd>
            <span>
              <b>{o.label}</b>
              <small>{o.hint}</small>
            </span>
          </button>
        ))}
        <div className="lp-dlg-f">
          <button type="button" className="lp-btn" style={{ height: 40, fontSize: 15 }} onClick={onClose}>
            <kbd style={{ height: 28 }}>Esc</kbd>Cancelar
          </button>
          <span>Repetición: la acción queda en el registro del turno de esta sesión, no se guarda.</span>
        </div>
      </div>
    </div>
  );
}
