import type { LineAlarmEvent, LineReplay, LineShift, RuleId } from "./types";

// IQ-F15: pure derivations of the line quality panel at a replay cursor.
// The backend engine decides when a rule fires (alarm events + per-piece rule
// state); this module only aggregates for display and applies the operator's
// session (acknowledge, actions) on top of those events.

/** Seconds without acknowledgement before an alarm escalates to the shift supervisor. */
export const ESCALATION_S: Record<1 | 2, number> = { 1: 90, 2: 180 };

export const pieceTs = (r: LineReplay, i: number): number => r.window.start_ts + r.pieces.t[i];

/** Index of the last piece at or before `t` (seconds from the window start); -1 before the first. */
export function indexAt(r: LineReplay, t: number): number {
  const ts = r.pieces.t;
  let lo = 0;
  let hi = ts.length - 1;
  let ans = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (ts[mid] <= t) {
      ans = mid;
      lo = mid + 1;
    } else hi = mid - 1;
  }
  return ans;
}

/** Plant-time clock (HH:MM:SS) of an epoch. */
export function plantClock(ts: number, offsetMinutes: number): string {
  return new Date((ts + offsetMinutes * 60) * 1000).toISOString().slice(11, 19);
}

export function shiftAt(r: LineReplay, ts: number): LineShift | null {
  return r.shifts.find((s) => s.start_ts <= ts && ts < s.end_ts) ?? null;
}

export interface ShiftCounts {
  shift: LineShift | null;
  pieces: number;
  nok: number;
  byNest: Map<number, [number, number]>;
  byCavity: Map<number, [number, number]>;
  byStation: Map<string, number>;
  /** hour start (epoch) → [pieces, nok] */
  hours: Map<number, [number, number]>;
}

function bump(map: Map<number, [number, number]>, key: number, bad: number) {
  const row = map.get(key) ?? [0, 0];
  row[0] += 1;
  row[1] += bad;
  map.set(key, row);
}

/** Shift-to-date counts at piece `idx`: the backend baseline (first shift only) plus the replayed pieces. */
export function shiftCounts(r: LineReplay, idx: number): ShiftCounts {
  const at = idx >= 0 ? pieceTs(r, idx) : r.window.start_ts + (r.pieces.t[0] ?? 0);
  const shift = shiftAt(r, at);
  const firstShift = r.pieces.t.length > 0 ? shiftAt(r, pieceTs(r, 0)) : null;
  const fromBaseline = shift !== null && firstShift !== null && shift.start_ts === firstShift.start_ts;
  const out: ShiftCounts = {
    shift,
    pieces: fromBaseline ? r.baseline.pieces : 0,
    nok: fromBaseline ? r.baseline.nok : 0,
    byNest: new Map(fromBaseline ? r.baseline.by_nest.map(([g, n, k]) => [g, [n, k]]) : []),
    byCavity: new Map(fromBaseline ? r.baseline.by_cavity.map(([g, n, k]) => [g, [n, k]]) : []),
    byStation: new Map(fromBaseline ? r.baseline.by_station : []),
    hours: new Map(fromBaseline ? r.baseline.hours.map(([h, n, k]) => [h, [n, k]]) : []),
  };
  const offset = r.utc_offset_minutes * 60;
  for (let i = 0; i <= idx; i++) {
    const ts = pieceTs(r, i);
    if (shift && ts < shift.start_ts) continue;
    const bad = r.pieces.nok[i];
    out.pieces += 1;
    out.nok += bad;
    const nest = r.pieces.nest[i];
    const cav = r.pieces.cavity[i];
    if (nest != null) bump(out.byNest, nest, bad);
    if (cav != null) bump(out.byCavity, cav, bad);
    const st = r.pieces.station[i];
    if (bad && st >= 0) {
      const key = r.line.stations[st].key;
      out.byStation.set(key, (out.byStation.get(key) ?? 0) + 1);
    }
    bump(out.hours, Math.floor((ts + offset) / 3600) * 3600 - offset, bad);
  }
  return out;
}

export interface Kpis {
  pieces: number;
  ok: number;
  nok: number;
  shiftRate: number | null;
  /** NOK rate of the R3 window, from the engine (null until the window is full). */
  windowRate: number | null;
  windowNok: number;
  piecesPerHour: number;
}

export function kpis(r: LineReplay, idx: number, counts: ShiftCounts): Kpis {
  let recent = 0;
  let windowNok = 0;
  if (idx >= 0) {
    const now = pieceTs(r, idx);
    for (let i = idx; i >= 0 && pieceTs(r, i) > now - 600; i--) recent++;
    for (let i = idx; i >= 0 && i > idx - r.rules.rate_window; i--) windowNok += r.pieces.nok[i];
  }
  return {
    pieces: counts.pieces,
    ok: counts.pieces - counts.nok,
    nok: counts.nok,
    shiftRate: counts.pieces ? counts.nok / counts.pieces : null,
    windowRate: idx >= 0 ? r.state.rate[idx] : null,
    windowNok,
    piecesPerHour: recent * 6,
  };
}

export interface NestWindow {
  nest: number;
  pieces: number;
  nok: number;
  rate: number | null;
}

/** NOK of the last `nest_window` pieces of each nest, and the pooled rate of all of them. */
export function nestWindows(r: LineReplay, idx: number): { nests: NestWindow[]; pooled: number | null } {
  const size = r.rules.nest_window;
  const acc = new Map<number, [number, number]>(r.line.nests.map((n) => [n, [0, 0]]));
  for (let i = idx; i >= 0; i--) {
    const nest = r.pieces.nest[i];
    if (nest == null) continue;
    const row = acc.get(nest);
    if (!row || row[0] >= size) continue;
    row[0] += 1;
    row[1] += r.pieces.nok[i];
    if ([...acc.values()].every(([n]) => n >= size)) break;
  }
  let n = 0;
  let k = 0;
  const nests = [...acc.entries()].map(([nest, [pieces, nok]]) => {
    n += pieces;
    k += nok;
    return { nest, pieces, nok, rate: pieces ? nok / pieces : null };
  });
  return { nests, pooled: n ? k / n : null };
}

/** Trailing consecutive NOK at `idx`, from the engine. */
export const streakAt = (r: LineReplay, idx: number): number => (idx >= 0 ? r.state.run[idx] : 0);

export interface NestProgress {
  nest: number;
  ratio: number;
  nok: number;
  /** 0..1+ : how close R2 is to firing; both the ratio and the minimum NOK count must hold. */
  progress: number;
}

/** Nest closest to R2 at the cursor (the engine's worst ratio, with its NOK count). */
export function nestProgress(r: LineReplay, idx: number): NestProgress | null {
  if (idx < 0) return null;
  const ratio = r.state.nest_ratio[idx];
  const nest = r.state.nest_ratio_nest[idx];
  if (ratio === null || nest === null) return null;
  const nok = nestWindows(r, idx).nests.find((n) => n.nest === nest)?.nok ?? 0;
  return { nest, ratio, nok, progress: Math.min(ratio / r.rules.nest_factor, nok / r.rules.nest_min_nok) };
}

/* ---------- operator session on top of the engine events ---------- */

export interface LogEntry {
  ts: number;
  text: string;
}

export interface PanelSession {
  acked: Record<string, number>;
  resolved: Record<string, true>;
  done: Record<string, boolean[]>;
  escalatedQuality: Record<string, true>;
  stopped: boolean;
  log: LogEntry[];
  /**
   * Alarms raised before this time (the replay's starting point) count as already
   * acknowledged: the replay starts mid-history, someone on the line saw them.
   */
  inheritedBefore: number | null;
}

export const emptySession = (): PanelSession => ({
  acked: {},
  resolved: {},
  done: {},
  escalatedQuality: {},
  stopped: false,
  log: [],
  inheritedBefore: null,
});

export type SessionAction =
  | { type: "reset"; ts: number; text: string; inheritBefore?: number }
  | { type: "ack"; id: string; ts: number }
  | { type: "act"; alarm: LineAlarmEvent; option: number; ts: number; contained: number };

const stepsDone = (s: PanelSession, id: string): boolean[] => s.done[id] ?? [false, false, false, false];

function withLog(s: PanelSession, ts: number, text: string): PanelSession {
  return { ...s, log: [{ ts, text }, ...s.log] };
}

export function sessionReducer(s: PanelSession, a: SessionAction): PanelSession {
  if (a.type === "reset") return withLog({ ...emptySession(), inheritedBefore: a.inheritBefore ?? null }, a.ts, a.text);
  if (a.type === "ack") {
    if (s.acked[a.id] !== undefined) return s;
    return withLog({ ...s, acked: { ...s.acked, [a.id]: a.ts } }, a.ts, `${a.id.split(":")[0]} reconocida`);
  }
  const { alarm, option, ts } = a;
  const id = alarm.id;
  const acked = s.acked[id] !== undefined ? s.acked : { ...s.acked, [id]: ts };
  const done = [...stepsDone(s, id)];
  const resolve = (next: PanelSession, text: string, resume: boolean) =>
    withLog({ ...next, resolved: { ...next.resolved, [id]: true }, stopped: resume ? false : next.stopped }, ts, text);
  if (alarm.rule === "R1") {
    if (option === 0) {
      done[0] = true;
      return withLog({ ...s, acked, done: { ...s.done, [id]: done }, stopped: true }, ts, "R1 · línea detenida por el operador");
    }
    if (option === 1) {
      done[0] = done[0] || s.stopped;
      done[1] = true;
      return withLog({ ...s, acked, done: { ...s.done, [id]: done } }, ts, `R1 · ${a.contained} pzs segregadas`);
    }
    if (option === 2) return resolve({ ...s, acked }, "R1 · causa corregida, producción reanudada", true);
    return resolve({ ...s, acked }, "R1 · cerrada como falsa alarma (para revisión)", true);
  }
  if (option === 0) {
    done[0] = true;
    return withLog({ ...s, acked, done: { ...s.done, [id]: done } }, ts, `${alarm.rule} · revisado, en observación`);
  }
  if (option === 1) return resolve({ ...s, acked }, `${alarm.rule} · ajuste realizado`, false);
  if (option === 2) {
    return withLog(
      { ...s, acked, escalatedQuality: { ...s.escalatedQuality, [id]: true } },
      ts,
      `${alarm.rule} · escalada a calidad`,
    );
  }
  return resolve({ ...s, acked }, `${alarm.rule} · cerrada como falsa alarma (para revisión)`, false);
}

/** When the alarm was acknowledged (inherited alarms: at their raise), or null. */
function ackedAt(s: PanelSession, ev: LineAlarmEvent): number | null {
  const own = s.acked[ev.id];
  if (own !== undefined) return own;
  return s.inheritedBefore !== null && ev.raised_ts < s.inheritedBefore ? ev.raised_ts : null;
}

export interface ActiveAlarm {
  ev: LineAlarmEvent;
  /** The rule condition still holds at the cursor (engine). */
  condition: boolean;
  acked: boolean;
  ackTs: number | null;
  done: boolean[];
  /** Seconds since the alarm was raised, in replay time. */
  elapsed: number;
  escalated: boolean;
  escalatedQuality: boolean;
}

/**
 * Alarms the panel shows at `idx`. R1 latches until the operator closes it;
 * R2/R3 leave once their condition is normal and they are acknowledged
 * (ISA-18.2: an unacknowledged return-to-normal stays visible); advisories
 * (priority 3) follow their condition. Events that started and ended before
 * the replay window only count while their condition holds.
 */
export function activeAlarms(r: LineReplay, idx: number, s: PanelSession): ActiveAlarm[] {
  if (idx < 0) return [];
  const now = pieceTs(r, idx);
  const out: ActiveAlarm[] = [];
  for (const ev of r.alarms) {
    if (ev.raised_index > idx || s.resolved[ev.id]) continue;
    const condition = ev.cleared_index === null || ev.cleared_index > idx;
    const inWindow = ev.raised_index >= 0 && r.pieces.t[ev.raised_index] >= 0;
    const ackTs = ackedAt(s, ev);
    const acked = ackTs !== null;
    const latched = inWindow && (ev.rule === "R1" || !acked);
    if (!(condition || (ev.priority < 3 && latched))) continue;
    const elapsed = now - ev.raised_ts;
    const limit = ev.priority === 1 ? ESCALATION_S[1] : ESCALATION_S[2];
    const escalated = ev.priority < 3 && (acked ? ackTs - ev.raised_ts >= limit : elapsed >= limit);
    out.push({
      ev,
      condition,
      acked,
      ackTs,
      done: stepsDone(s, ev.id),
      elapsed,
      escalated,
      escalatedQuality: !!s.escalatedQuality[ev.id],
    });
  }
  return out.sort(
    (a, b) => a.ev.priority - b.ev.priority || Number(a.acked) - Number(b.acked) || a.ev.raised_ts - b.ev.raised_ts,
  );
}

export const operatorAlarms = (alarms: ActiveAlarm[]) => alarms.filter((a) => a.ev.priority < 3);
export const advisories = (alarms: ActiveAlarm[]) => alarms.filter((a) => a.ev.priority === 3);

/** Pieces from the evidence start (first NOK of the streak) up to the cursor: what to contain. */
export function piecesToContain(ev: LineAlarmEvent, idx: number): number {
  return Math.max(0, idx - Math.max(ev.evidence_from_index, 0) + 1);
}

/** Pieces drawn red: NOK of every R1 streak already raised at the cursor (evidence → clear). */
export function streakPieces(r: LineReplay, idx: number): Set<number> {
  const hot = new Set<number>();
  for (const ev of r.alarms) {
    if (ev.rule !== "R1" || ev.raised_index > idx) continue;
    const end = Math.min(idx, ev.cleared_index === null ? idx : ev.cleared_index - 1);
    for (let i = Math.max(ev.evidence_from_index, 0); i <= end; i++) if (r.pieces.nok[i]) hot.add(i);
  }
  return hot;
}

/** Engine events and operator entries of the shift log, newest first. */
export function shiftLog(r: LineReplay, idx: number, s: PanelSession, limit = 8): LogEntry[] {
  if (idx < 0) return s.log.slice(0, limit);
  const now = pieceTs(r, idx);
  const engine: LogEntry[] = [];
  for (const ev of r.alarms) {
    if (ev.raised_index < 0 || ev.raised_index > idx || r.pieces.t[ev.raised_index] < 0) continue;
    engine.push({ ts: ev.raised_ts, text: `${ev.rule} activada · ${shortWhat(r, ev)}` });
    const limitS = ev.priority === 1 ? ESCALATION_S[1] : ESCALATION_S[2];
    const ack = ackedAt(s, ev) ?? undefined;
    if (ev.priority < 3 && ev.raised_ts + limitS <= now && (ack === undefined || ack - ev.raised_ts >= limitS)) {
      engine.push({ ts: ev.raised_ts + limitS, text: `${ev.rule} escalada a supervisor de turno (sin reconocer)` });
    }
  }
  return [...engine, ...s.log].sort((a, b) => b.ts - a.ts).slice(0, limit);
}

/* ---------- texts ---------- */

const pct = (x: number | null, digits = 1) =>
  x === null ? "—" : `${(x * 100).toLocaleString("es-MX", { minimumFractionDigits: digits, maximumFractionDigits: digits })} %`;
export const fmtPct = pct;
export const fmtInt = (n: number) => Math.round(n).toLocaleString("es-MX");
export const fmtRatio = (x: number | null) =>
  x === null ? "—" : `${x.toLocaleString("es-MX", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}×`;

/** R1 `nests` has one entry per streak piece (in order, repeats included); this is the distinct list. */
export const distinctNests = (ev: LineAlarmEvent): number[] => [...new Set(ev.nests)];

export function stationName(r: LineReplay, key: string | null): string | null {
  if (!key) return null;
  return r.line.stations.find((s) => s.key === key)?.name ?? key;
}

export const RULE_TITLE: Record<RuleId, (ev: LineAlarmEvent) => string> = {
  R1: () => "PARAR LÍNEA",
  R2: (ev) => `REVISAR NIDO ${ev.key}`,
  R3: () => "TASA NOK ALTA",
  R4: (ev) => `CAVIDAD ${ev.key}`,
};

function shortWhat(r: LineReplay, ev: LineAlarmEvent): string {
  if (ev.rule === "R1") return `${r.rules.run_limit} NOK consecutivas`;
  if (ev.rule === "R2") return `nido ${ev.key} a ${fmtRatio(ev.value)} el resto`;
  if (ev.rule === "R3") return `${pct(ev.value)} NOK en últimas ${r.rules.rate_window}`;
  return `cavidad ${ev.key} a ${pct(ev.value)} NOK`;
}

/** What happened, with the live value at the cursor where the rule has one. */
export function whatText(r: LineReplay, ev: LineAlarmEvent, idx: number): string {
  if (ev.rule === "R1") return `${ev.nests.length || r.rules.run_limit} NOK consecutivas`;
  if (ev.rule === "R2") {
    const w = nestWindows(r, idx);
    const nest = w.nests.find((n) => n.nest === ev.key);
    const rest = w.nests.filter((n) => n.nest !== ev.key);
    const rn = rest.reduce((s, n) => s + n.pieces, 0);
    const rk = rest.reduce((s, n) => s + n.nok, 0);
    return `Nido ${ev.key}: ${pct(nest?.rate ?? null)} NOK vs ${pct(rn ? rk / rn : null)} del resto`;
  }
  if (ev.rule === "R3") return `${pct(r.state.rate[idx] ?? ev.value)} NOK en las últimas ${r.rules.rate_window} piezas`;
  return `Cavidad ${ev.key}: ${pct(ev.value)} NOK en sus últimas ${r.rules.cavity_window} piezas`;
}

export function whereText(r: LineReplay, ev: LineAlarmEvent): string {
  const st = stationName(r, ev.station);
  if (ev.rule === "R1") return [ev.nests.length ? `Nidos ${distinctNests(ev).join(", ")}` : "Línea", st].filter(Boolean).join(" · ");
  if (ev.rule === "R2") return st ?? `Nido ${ev.key}`;
  if (ev.rule === "R3") return ["Toda la línea", st].filter(Boolean).join(" · ");
  return `Cavidad de molde ${ev.key}`;
}

export function steps(r: LineReplay, ev: LineAlarmEvent, idx: number): string[] {
  const st = stationName(r, ev.station);
  const from = plantClock(ev.evidence_from_ts, r.utc_offset_minutes);
  if (ev.rule === "R1") {
    const distinct = new Set(ev.nests).size;
    return [
      "Detener la inyección (paro de línea)",
      `Segregar piezas desde ${from} · ${fmtInt(piecesToContain(ev, idx))} pzs`,
      distinct > 1
        ? `Revisar molde e insertos${st ? `: falla en ${st}` : ""} en ${distinct} nidos distintos`
        : `Revisar el nido ${ev.nests[0] ?? ""}${st ? ` · ${st}` : ""}`,
      "Registrar causa y reanudar",
    ];
  }
  if (ev.rule === "R2") {
    return [
      `Revisar pines y posicionador del nido ${ev.key}`,
      `Verificar las próximas 5 piezas del nido ${ev.key}`,
      `Si persiste: bloquear el nido ${ev.key} y avisar a calidad`,
      "Registrar resultado",
    ];
  }
  return [
    "Avisar al técnico de calidad del turno",
    st ? `Revisar la estación ${st}` : "Revisar la estación que más rechaza",
    "Revisar los nidos y cavidades con más NOK",
    "Registrar resultado",
  ];
}

export const currentStep = (done: boolean[]) => {
  const i = done.indexOf(false);
  return i < 0 ? 3 : i;
};

export function actionOptions(r: LineReplay, ev: LineAlarmEvent, idx: number): { label: string; hint: string }[] {
  if (ev.rule === "R1") {
    return [
      { label: "Línea detenida", hint: "Paro confirmado por el operador (pausa la repetición)" },
      {
        label: "Piezas segregadas",
        hint: `Desde ${plantClock(ev.evidence_from_ts, r.utc_offset_minutes)} · ${fmtInt(piecesToContain(ev, idx))} pzs a contención`,
      },
      { label: "Causa corregida — reanudar", hint: "Cierra la alarma y reanuda la repetición" },
      { label: "Falsa alarma", hint: "Cierra la alarma; queda para revisión de calidad" },
    ];
  }
  return [
    { label: "Revisado — en observación", hint: "Reconoce y mantiene la vigilancia" },
    { label: "Ajuste realizado", hint: "Cierra la alarma" },
    { label: "Escalar a calidad", hint: "Notifica al técnico de calidad del turno" },
    { label: "Falsa alarma", hint: "Cierra la alarma; queda para revisión de calidad" },
  ];
}

export function whyText(r: LineReplay, ev: LineAlarmEvent): string {
  const ref = pct(r.rules.reference_nok_rate);
  if (ev.rule === "R1") {
    const distinct = new Set(ev.nests).size;
    return distinct > 1
      ? `Varios nidos fallan seguidos: apunta a una causa común (molde, inyección), no a un nido. Con una tasa de referencia de ${ref}, ${r.rules.run_limit} NOK seguidas casi nunca ocurren por azar.`
      : `Con una tasa de referencia de ${ref}, ${r.rules.run_limit} NOK seguidas casi nunca ocurren por azar.`;
  }
  if (ev.rule === "R2") {
    return `Solo el nido ${ev.key} se separa del resto: apunta a pines, posicionador o suciedad de ese nido, no al proceso completo.`;
  }
  return `La tasa supera ${fmtRatio(r.rules.rate_factor)} la referencia histórica de la línea (${ref}).`;
}
