import clsx from "clsx";
import {
  advisories,
  currentStep,
  fmtInt,
  fmtPct,
  nestWindows,
  operatorAlarms,
  plantClock,
  RULE_TITLE,
  shiftLog,
  steps,
  whatText,
  whereText,
} from "../../../lib/line-panel/model";
import type { LineReplay } from "../../../lib/line-panel/types";
import { Bullet, LpSymbol, Panel, StepList, StreakMeter, escalationLeft, type PanelView } from "../parts";

// View B — Process map: for the line lead / quality technician. Where the NOK
// comes from (nest, mold cavity, station, hour) next to the alarms and the log.

const mmss = (s: number) => {
  const d = Math.max(0, Math.floor(s));
  return `${String(Math.floor(d / 60)).padStart(2, "0")}:${String(d % 60).padStart(2, "0")}`;
};

function NestChart({ view, w, h }: { view: PanelView; w: number; h: number }) {
  const { r, idx, alarms } = view;
  const { nests, pooled } = nestWindows(r, idx);
  const top = Math.max(0.1, ...nests.map((n) => n.rate ?? 0), (pooled ?? 0) * r.rules.nest_factor);
  const max = Math.ceil((top * 100) / 10) * 10;
  const pl = 44;
  const pb = 30;
  const pt = 34;
  const cw = (w - pl) / nests.length;
  const y = (v: number) => pt + (h - pt - pb) * (1 - Math.min(v * 100, max) / max);
  const ticks = Array.from({ length: max / 10 + 1 }, (_, i) => i * 10);
  const lim = pooled === null ? null : pooled * r.rules.nest_factor;
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} role="img" aria-label="NOK por nido">
      {ticks.map((v) => (
        <g key={v}>
          <line x1={pl} x2={w} y1={y(v / 100)} y2={y(v / 100)} stroke="var(--border-default)" />
          <text x={pl - 8} y={y(v / 100) + 5} textAnchor="end" fontSize={13} fill="var(--text-secondary)">
            {v}%
          </text>
        </g>
      ))}
      {nests.map((n, i) => {
        const al = alarms.find((a) => a.ev.rule === "R2" && a.ev.key === n.nest);
        const x = pl + i * cw + cw * 0.2;
        const bw = cw * 0.6;
        const v = n.rate ?? 0;
        return (
          <g key={n.nest}>
            <rect x={x} y={y(v)} width={bw} height={y(0) - y(v)} rx={2} fill={al ? "var(--lp-p2-fill)" : "var(--lp-bar)"} />
            <text x={x + bw / 2} y={y(v) - 8} textAnchor="middle" fontSize={15} fontWeight={600} className="lp-num" fill="var(--text-primary)">
              {n.rate === null ? "—" : Math.round(v * 100)}
            </text>
            <text x={x + bw / 2} y={h - 8} textAnchor="middle" fontSize={15} fontWeight={al ? 700 : 500} fill="var(--text-primary)">
              N{n.nest}
            </text>
            {al && (
              <g transform={`translate(${x + bw / 2 - 13},${y(v) - 52})`}>
                <LpSymbol priority={2} size={26} blinking={!al.acked} />
              </g>
            )}
          </g>
        );
      })}
      {lim !== null && (
        <g>
          <line x1={pl} x2={w} y1={y(lim)} y2={y(lim)} stroke="var(--text-primary)" strokeWidth={2} strokeDasharray="7 5" />
          <text x={w - 4} y={y(lim) - 7} textAnchor="end" fontSize={13} fontWeight={700} fill="var(--text-primary)">
            {r.rules.nest_factor}× RESTO = {fmtPct(lim)}
          </text>
        </g>
      )}
    </svg>
  );
}

function hourLabel(r: LineReplay, ts: number) {
  return `${plantClock(ts, r.utc_offset_minutes).slice(0, 2)}h`;
}

function TrendChart({ view, w, h }: { view: PanelView; w: number; h: number }) {
  const { r, idx, counts } = view;
  const shift = counts.shift;
  if (!shift) return null;
  const hours = Array.from({ length: Math.round((shift.end_ts - shift.start_ts) / 3600) }, (_, i) => shift.start_ts + i * 3600);
  const rates = hours.map((hs) => {
    const row = counts.hours.get(hs);
    return row && row[0] ? row[1] / row[0] : null;
  });
  const lim = r.rules.rate_limit;
  const ref = r.rules.reference_nok_rate;
  const max = Math.ceil((Math.max(lim * 1.4, ...rates.map((x) => x ?? 0)) * 100) / 10) * 10;
  const pl = 44;
  const pb = 28;
  const pt = 12;
  const cw = (w - pl) / hours.length;
  const y = (v: number) => pt + (h - pt - pb) * (1 - Math.min(v * 100, max) / max);
  const nowTs = idx >= 0 ? r.window.start_ts + r.pieces.t[idx] : shift.start_ts;
  const ticks = Array.from({ length: max / 10 + 1 }, (_, i) => i * 10);
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} role="img" aria-label="NOK por hora del turno">
      {ticks.map((v) => (
        <g key={v}>
          <line x1={pl} x2={w} y1={y(v / 100)} y2={y(v / 100)} stroke="var(--border-default)" />
          <text x={pl - 8} y={y(v / 100) + 5} textAnchor="end" fontSize={13} fill="var(--text-secondary)">
            {v}%
          </text>
        </g>
      ))}
      {hours.map((hs, i) => {
        const v = rates[i];
        const x = pl + i * cw + cw * 0.22;
        const bw = cw * 0.56;
        const current = nowTs >= hs && nowTs < hs + 3600;
        return (
          <g key={hs}>
            {v !== null && (
              <>
                <rect
                  x={x}
                  y={y(v)}
                  width={bw}
                  height={y(0) - y(v)}
                  rx={2}
                  fill={v >= lim ? "var(--lp-p2-fill)" : "var(--lp-bar)"}
                  stroke={current ? "var(--text-primary)" : "none"}
                  strokeWidth={current ? 2 : 0}
                  strokeDasharray={current ? "4 3" : undefined}
                />
                <text x={x + bw / 2} y={y(v) - 6} textAnchor="middle" fontSize={14} fontWeight={600} fill="var(--text-primary)">
                  {(v * 100).toFixed(1)}
                </text>
              </>
            )}
            <text x={x + bw / 2} y={h - 6} textAnchor="middle" fontSize={14} fill="var(--text-secondary)">
              {hourLabel(r, hs)}
              {current ? " · en curso" : ""}
            </text>
          </g>
        );
      })}
      <line x1={pl} x2={w} y1={y(ref)} y2={y(ref)} stroke="var(--text-secondary)" strokeWidth={1.5} strokeDasharray="3 4" />
      <text x={w - 4} y={y(ref) - 6} textAnchor="end" fontSize={13} fill="var(--text-secondary)">
        REF. {fmtPct(ref)}
      </text>
      <line x1={pl} x2={w} y1={y(lim)} y2={y(lim)} stroke="var(--text-primary)" strokeWidth={2} strokeDasharray="7 5" />
      <text x={w - 4} y={y(lim) - 6} textAnchor="end" fontSize={13} fontWeight={700} fill="var(--text-primary)">
        ALARMA {fmtPct(lim, 0)}
      </text>
    </svg>
  );
}

export function ProcessMapView(view: PanelView) {
  const { r, idx, k, alarms, counts, session } = view;
  const ops = operatorAlarms(alarms);
  const cavRate = (key: number | null) => {
    const row = key === null ? undefined : counts.byCavity.get(key);
    return row && row[0] ? row[1] / row[0] : 0;
  };
  const adv = [...advisories(alarms)].sort((x, y) => cavRate(y.ev.key) - cavRate(x.ev.key));
  const sel = ops[0];
  const stationTotal = [...counts.byStation.values()].reduce((s, n) => s + n, 0) || 1;
  const cavCount = r.line.mold_cavities ?? 0;
  const ref = r.rules.reference_nok_rate;

  return (
    <main className="lp-main lp-B">
      <div className="lp-col">
        <div className="lp-panel lp-ktile">
          <div className="lp-label">Piezas producidas</div>
          <div className="val">{fmtInt(k.pieces)}</div>
          <div className="foot">{fmtInt(k.piecesPerHour)} pzs/h</div>
        </div>
        <div className="lp-panel lp-ktile">
          <div className="lp-label">OK</div>
          <div className="val">{fmtInt(k.ok)}</div>
          <div className="foot">{fmtPct(k.pieces ? k.ok / k.pieces : null)} del turno</div>
        </div>
        <div className="lp-panel lp-ktile">
          <div className="lp-label">NOK</div>
          <div className="val">{fmtInt(k.nok)}</div>
          <div className="foot">
            {fmtPct(k.shiftRate)} del turno · ref. {fmtPct(ref)}
          </div>
        </div>
        <div className="lp-panel lp-ktile">
          <div className="lp-label">NOK últimas {r.rules.rate_window}</div>
          <div className="val">
            {k.windowRate === null ? "—" : (k.windowRate * 100).toFixed(1)}
            <small>%</small>
          </div>
          <Bullet value={k.windowRate} max={Math.max(r.rules.rate_limit * 2, 0.05)} reference={ref} limit={r.rules.rate_limit} />
        </div>
        <div className="lp-panel lp-ktile" style={{ flex: 1.2 }}>
          <div className="lp-label">Racha NOK actual</div>
          <div style={{ marginTop: 8 }}>
            <StreakMeter r={r} idx={idx} alarms={alarms} scale={0.86} stacked />
          </div>
        </div>
      </div>

      <div className="lp-col">
        <Panel
          title={`NOK por nido · últimas ${r.rules.nest_window} piezas de cada nido`}
          aside={`R2: alarma si un nido ≥ ${r.rules.nest_factor}× el resto`}
          style={{ flex: "none", height: 318 }}
        >
          <div style={{ padding: "6px 16px 4px" }}>
            <NestChart view={view} w={956} h={258} />
          </div>
        </Panel>
        <div style={{ display: "grid", gridTemplateColumns: cavCount ? "1fr 372px" : "1fr", gap: 16, flex: 1, minHeight: 0 }}>
          {cavCount > 0 && (
            <Panel title="Cavidades de molde · % NOK del turno" aside={`■ aviso ≥ ${fmtPct(r.rules.cavity_limit, 0)} (últ. ${r.rules.cavity_window})`}>
              <div className="lp-pb" style={{ padding: "12px 14px" }}>
                <div className="lp-cavgrid">
                  {Array.from({ length: cavCount }, (_, i) => {
                    const row = counts.byCavity.get(i + 1);
                    const rate = row && row[0] ? row[1] / row[0] : 0;
                    const a = Math.min(1, rate / 0.45);
                    const isAdv = adv.some((x) => x.ev.key === i + 1);
                    return (
                      <div
                        key={i}
                        className={clsx("lp-cav", isAdv && "adv")}
                        style={{
                          background: `rgba(var(--lp-ramp), ${(0.08 + a * 0.85).toFixed(2)})`,
                          color: a > 0.5 ? "var(--bg-surface)" : "var(--text-primary)",
                        }}
                      >
                        <span className="c">C{i + 1}</span>
                        <span className="r">{row && row[0] ? `${Math.round(rate * 100)}%` : "—"}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </Panel>
          )}
          <Panel title="Dónde falla · 1ª estación">
            <div className="lp-pb">
              {r.line.stations.length ? (
                <>
                  <div className="lp-stbar">
                    {r.line.stations.map((s) => {
                      const n = counts.byStation.get(s.key) ?? 0;
                      return (
                        <div key={s.key} style={{ display: "contents" }}>
                          <span>{s.name}</span>
                          <span className="b">
                            <i style={{ width: `${(100 * n) / stationTotal}%` }} />
                          </span>
                          <span className="p">{Math.round((100 * n) / stationTotal)}%</span>
                        </div>
                      );
                    })}
                  </div>
                  <div className="lp-muted" style={{ fontSize: 14, marginTop: 14 }}>
                    NOK atribuido a la primera estación que falla en el orden del proceso.
                  </div>
                </>
              ) : (
                <div className="lp-empty" style={{ fontSize: 16 }}>
                  Este dataset no trae estaciones de inspección: el NOK es por cotas fuera de tolerancia.
                </div>
              )}
            </div>
          </Panel>
        </div>
        <Panel title={`NOK por hora · turno ${counts.shift?.label ?? ""}`} style={{ flex: "none", height: 226 }}>
          <div style={{ padding: "6px 16px 0" }}>
            <TrendChart view={view} w={956} h={170} />
          </div>
        </Panel>
      </div>

      <div className="lp-col">
        <Panel
          title={`Alarmas activas (${ops.length})`}
          aside={
            ops.some((x) => !x.acked) && (
              <>
                <span className="lp-kbd">R</span>&nbsp;reconocer
              </>
            )
          }
          style={{ flex: 1 }}
        >
          <div className="lp-pb lp-alist">
            {ops.length === 0 ? (
              <div className="lp-empty">
                Sin alarmas activas
                <br />
                <span style={{ fontSize: 15 }}>Reglas R1–R{r.line.mold_cavities ? 4 : 3} en vigilancia</span>
              </div>
            ) : (
              <>
                {ops.slice(0, 3).map((a) => (
                  <div key={a.ev.id} className={clsx("lp-acard", `p${a.ev.priority}`)}>
                    <div className="h">
                      <LpSymbol priority={a.ev.priority} size={28} blinking={!a.acked} />
                      {a.ev.rule} · {RULE_TITLE[a.ev.rule](a.ev)}
                      <span className="tm">{plantClock(a.ev.raised_ts, r.utc_offset_minutes)}</span>
                    </div>
                    <div className="d">
                      {whatText(r, a.ev, idx)} · {whereText(r, a.ev)}
                    </div>
                    <div className="s">
                      {a.acked
                        ? `Reconocida · paso ${currentStep(a.done) + 1}/4`
                        : `Sin reconocer ${mmss(a.elapsed)} · ${a.escalated ? "escalada" : `escala en ${mmss(escalationLeft(a))}`}`}
                      {a.ev.rule === "R1" && session.stopped ? " · línea detenida" : ""}
                    </div>
                    {a === sel && ops.length > 1 && <div className="nx">→ {steps(r, a.ev, idx)[currentStep(a.done)]}</div>}
                  </div>
                ))}
                {ops.length === 1 && sel && (
                  <div style={{ marginTop: 6 }}>
                    <StepList items={steps(r, sel.ev, idx)} done={sel.done} size={17} />
                  </div>
                )}
              </>
            )}
          </div>
        </Panel>
        {r.line.mold_cavities ? (
          <Panel title={`Avisos (${adv.length}) · no requieren paro`} aside={adv.length > 3 ? "los 3 más altos" : undefined} style={{ flex: "none" }}>
            <div className="lp-pb" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {adv.length === 0 ? (
                <span className="lp-muted">Sin avisos</span>
              ) : (
                adv.slice(0, 3).map((v) => (
                  <div key={v.ev.id} className="lp-adv">
                    <span style={{ marginTop: 2 }}>
                      <LpSymbol priority={3} size={20} />
                    </span>
                    <span>
                      <b>
                        Cavidad {v.ev.key}: {fmtPct(cavRate(v.ev.key), 0)} NOK en el turno
                      </b>
                      <br />
                      <span className="lp-muted">Herramental en el próximo cambio · aviso desde {plantClock(v.ev.raised_ts, r.utc_offset_minutes).slice(0, 5)}</span>
                    </span>
                  </div>
                ))
              )}
            </div>
          </Panel>
        ) : null}
        <Panel title="Registro del turno" style={{ flex: "none", height: 206 }}>
          <div className="lp-pb" style={{ paddingTop: 12 }}>
            <ul className="lp-log">
              {shiftLog(r, idx, session, 5).map((l, i) => (
                <li key={`${l.ts}-${i}`}>
                  <span className="tm">{plantClock(l.ts, r.utc_offset_minutes).slice(0, 5)}</span>
                  <span>{l.text}</span>
                </li>
              ))}
            </ul>
          </div>
        </Panel>
      </div>
    </main>
  );
}
