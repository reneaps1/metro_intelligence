import { describe, expect, it } from "vitest";
import { LINE_T0, makeLineReplay } from "../../test/linePanelFixtures";
import {
  activeAlarms,
  emptySession,
  indexAt,
  kpis,
  piecesToContain,
  plantClock,
  sessionReducer,
  shiftCounts,
  streakPieces,
} from "./model";
import type { LineReplay } from "./types";

describe("line panel model", () => {
  it("finds the piece at the replay cursor", () => {
    const r = makeLineReplay(false);
    expect(indexAt(r, -100)).toBe(-1);
    expect(indexAt(r, -20)).toBe(0);
    expect(indexAt(r, 0)).toBe(10);
    expect(indexAt(r, 1.9)).toBe(10);
    expect(indexAt(r, 10_000)).toBe(39);
  });

  it("shows the plant clock", () => {
    expect(plantClock(LINE_T0, -300)).toBe(new Date((LINE_T0 - 18_000) * 1000).toISOString().slice(11, 19));
  });

  it("adds the replayed pieces to the shift baseline", () => {
    const r = makeLineReplay(false);
    const c = shiftCounts(r, 10);
    const nokReplayed = r.pieces.nok.slice(0, 11).reduce((s, v) => s + v, 0);
    expect(c.shift?.label).toBe("06:00–14:00");
    expect(c.pieces).toBe(1011);
    expect(c.nok).toBe(100 + nokReplayed);
    expect(kpis(r, 10, c).ok).toBe(1011 - c.nok);
  });

  it("restarts the counts when the cursor enters the next shift", () => {
    const r: LineReplay = { ...makeLineReplay(false) };
    const shiftChange = r.shifts[1].start_ts - r.window.start_ts;
    r.pieces = { ...r.pieces, t: r.pieces.t.map((x, i) => (i >= 20 ? shiftChange + i : x)) };
    const c = shiftCounts(r, 25);
    expect(c.shift?.label).toBe("14:00–22:00");
    expect(c.pieces).toBe(6);
  });

  it("latches R1 until the operator closes it", () => {
    const r = makeLineReplay(true);
    expect(activeAlarms(r, 9, emptySession())).toHaveLength(0);
    const raised = activeAlarms(r, 10, emptySession());
    expect(raised[0].ev.rule).toBe("R1");
    expect(raised[0].condition).toBe(true);
    // condition cleared at piece 11, the alarm stays until it is closed
    const later = activeAlarms(r, 20, emptySession());
    expect(later[0].condition).toBe(false);
    let s = sessionReducer(emptySession(), { type: "act", alarm: r.alarms[0], option: 2, ts: LINE_T0 + 30, contained: 9 });
    expect(activeAlarms(r, 20, s)).toHaveLength(0);
    s = sessionReducer(emptySession(), { type: "act", alarm: r.alarms[0], option: 0, ts: LINE_T0 + 30, contained: 9 });
    expect(s.stopped).toBe(true);
    expect(activeAlarms(r, 20, s)[0].done[0]).toBe(true);
  });

  it("drops an acknowledged R2 once its condition is normal, keeps it while unacknowledged", () => {
    const base = makeLineReplay(false);
    const ev = { ...makeLineReplay(true).alarms[0], id: "R2:2:9015", rule: "R2" as const, priority: 2 as const, key: 2, raised_index: 15, raised_ts: LINE_T0 + 10, cleared_index: 18, cleared_ts: LINE_T0 + 16 };
    const r = { ...base, alarms: [ev] };
    expect(activeAlarms(r, 20, emptySession())).toHaveLength(1);
    const acked = sessionReducer(emptySession(), { type: "ack", id: ev.id, ts: LINE_T0 + 12 });
    expect(activeAlarms(r, 20, acked)).toHaveLength(0);
    expect(activeAlarms(r, 16, acked)).toHaveLength(1);
  });

  it("ignores events that started and ended before the window", () => {
    const base = makeLineReplay(true);
    const r = { ...base, alarms: [{ ...base.alarms[0], raised_index: 3, cleared_index: 5 }] };
    expect(activeAlarms(r, 4, emptySession())).toHaveLength(1);
    expect(activeAlarms(r, 12, emptySession())).toHaveLength(0);
  });

  it("escalates an unacknowledged priority-1 alarm after 90 s of replay time", () => {
    const base = makeLineReplay(true);
    const r = { ...base, pieces: { ...base.pieces, t: base.pieces.t.map((x, i) => (i > 10 ? x * 10 : x)) } };
    expect(activeAlarms(r, 14, emptySession())[0].escalated).toBe(false);
    expect(activeAlarms(r, 15, emptySession())[0].escalated).toBe(true);
    const acked = sessionReducer(emptySession(), { type: "ack", id: "R1::9010", ts: LINE_T0 + 5 });
    expect(activeAlarms(r, 15, acked)[0].escalated).toBe(false);
  });

  it("treats alarms raised before the replay start as already acknowledged", () => {
    const r = makeLineReplay(true);
    const inherited = sessionReducer(emptySession(), { type: "reset", ts: LINE_T0 + 1, text: "x", inheritBefore: LINE_T0 + 1 });
    const [a] = activeAlarms(r, 12, inherited);
    expect(a.acked).toBe(true);
    expect(a.escalated).toBe(false);
    const fresh = sessionReducer(emptySession(), { type: "reset", ts: LINE_T0, text: "x", inheritBefore: LINE_T0 });
    expect(activeAlarms(r, 12, fresh)[0].acked).toBe(false);
  });

  it("counts the pieces to contain and paints the streak red", () => {
    const r = makeLineReplay(true);
    expect(piecesToContain(r.alarms[0], 12)).toBe(7);
    expect([...streakPieces(r, 12)].sort((a, b) => a - b)).toEqual([6, 7, 8, 9, 10]);
    expect(streakPieces(r, 9).size).toBe(0);
  });
});
