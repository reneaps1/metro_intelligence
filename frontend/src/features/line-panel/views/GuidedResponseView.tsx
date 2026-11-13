import clsx from "clsx";
import {
  actionOptions,
  advisories,
  currentStep,
  distinctNests,
  fmtInt,
  fmtPct,
  fmtRatio,
  nestProgress,
  operatorAlarms,
  piecesToContain,
  plantClock,
  RULE_TITLE,
  shiftLog,
  stationName,
  steps,
  streakAt,
  whatText,
  whyText,
} from "../../../lib/line-panel/model";
import { AlarmTimer, LpSymbol, Panel, PieceStrip, StepList, StripLegend, escalationLeft, type PanelView } from "../parts";

// View C — Guided response: calm, it shows how close each rule is to asking
// for action; with an alarm, the screen becomes the case and its four steps.

const mmss = (s: number) => {
  const d = Math.max(0, Math.floor(s));
  return `${String(Math.floor(d / 60)).padStart(2, "0")}:${String(d % 60).padStart(2, "0")}`;
};

function advisorySummary(adv: ReturnType<typeof advisories>): string {
  if (!adv.length) return "Sin avisos";
  const worst = [...adv].sort((x, y) => y.ev.value - x.ev.value);
  const names = worst.slice(0, 3).map((v) => `C${v.ev.key}`).join(" · ");
  return `${names}${adv.length > 3 ? ` +${adv.length - 3}` : ""} → herramental`;
}

function Meter({ value, max, limit, label, cls }: { value: number; max: number; limit: number; label: string; cls?: string }) {
  return (
    <div className="lp-meter">
      <div className={clsx("fill", cls)} style={{ width: `${Math.min(100, (100 * value) / max)}%` }} />
      <div className="lim" style={{ left: `${(100 * limit) / max}%` }} />
      <div className="liml" style={{ left: `${(100 * limit) / max}%` }}>
        {label}
      </div>
    </div>
  );
}

function CalmView(view: PanelView) {
  const { r, idx, k, alarms } = view;
  const run = streakAt(r, idx);
  const np = nestProgress(r, idx);
  const cavRate = idx >= 0 ? r.state.cavity_rate[idx] : null;
  const cavWorst = idx >= 0 ? r.state.cavity_worst[idx] : null;
  const adv = advisories(alarms);
  const rules = [
    {
      code: "R1",
      name: "Racha NOK consecutiva",
      cons: (
        <>
          Al llegar a {r.rules.run_limit} → <b>PARAR LÍNEA</b> y segregar
        </>
      ),
      meter: <Meter value={run} max={r.rules.run_limit + 1} limit={r.rules.run_limit} label={`PARO · ${r.rules.run_limit}`} cls={run >= r.rules.run_limit ? "p1" : undefined} />,
      big: (
        <>
          {run}
          <span className="lp-muted" style={{ fontSize: "0.55em" }}>
            {" "}
            / {r.rules.run_limit}
          </span>
        </>
      ),
      sm: run ? `a ${r.rules.run_limit - run} pzs del paro` : "sin racha",
    },
    {
      code: "R2",
      name: "Nido más alto vs. el resto",
      cons: (
        <>
          ≥ {r.rules.nest_factor}× (últimas {r.rules.nest_window} del nido) → <b>REVISAR NIDO</b>
        </>
      ),
      // The meter shows the condition still missing: ratio or minimum NOK count, whichever is further.
      meter: <Meter value={np?.progress ?? 0} max={1.5} limit={1} label={`ALARMA · ${r.rules.nest_factor}× y ${r.rules.nest_min_nok} NOK`} />,
      big: <>{fmtRatio(np?.ratio ?? null)}</>,
      sm: np ? `nido ${np.nest} · ${np.nok} de ${r.rules.nest_min_nok} NOK mínimas` : "ventanas incompletas",
    },
    {
      code: "R3",
      name: `NOK en las últimas ${r.rules.rate_window} piezas`,
      cons: (
        <>
          ≥ {fmtPct(r.rules.rate_limit, 0)} → <b>AVISAR A CALIDAD</b>
        </>
      ),
      meter: <Meter value={k.windowRate ?? 0} max={r.rules.rate_limit * 1.5} limit={r.rules.rate_limit} label={`ALARMA · ${fmtPct(r.rules.rate_limit, 0)}`} />,
      big: <>{fmtPct(k.windowRate)}</>,
      sm: `ref. histórica ${fmtPct(r.rules.reference_nok_rate)}`,
    },
  ];
  if (r.line.mold_cavities) {
    rules.push({
      code: "R4",
      name: "Cavidad de molde más alta",
      cons: (
        <>
          ≥ {fmtPct(r.rules.cavity_limit, 0)} (últ. {r.rules.cavity_window}) → <b>aviso a herramental</b>, sin paro
        </>
      ),
      meter: <Meter value={cavRate ?? 0} max={r.rules.cavity_limit * 1.6} limit={r.rules.cavity_limit} label={`AVISO · ${fmtPct(r.rules.cavity_limit, 0)}`} />,
      big: <>{cavWorst !== null ? `C${cavWorst} · ${fmtPct(cavRate, 0)}` : "—"}</>,
      sm: adv.length ? `aviso abierto · ${adv.map((a) => `C${a.ev.key}`).join(", ")}` : "sin aviso",
    });
  }
  return (
    <main className="lp-main lp-C">
      <section className="lp-kpis4">
        <div className="lp-panel lp-tile">
          <div className="lbl">Piezas producidas</div>
          <div className="val" style={{ fontSize: 88 }}>
            {fmtInt(k.pieces)}
          </div>
          <div className="foot">{fmtInt(k.piecesPerHour)} pzs/h</div>
        </div>
        <div className="lp-panel lp-tile">
          <div className="lbl">OK</div>
          <div className="val" style={{ fontSize: 88 }}>
            {fmtInt(k.ok)}
          </div>
          <div className="foot">{fmtPct(k.pieces ? k.ok / k.pieces : null)} del turno</div>
        </div>
        <div className="lp-panel lp-tile">
          <div className="lbl">NOK</div>
          <div className="val" style={{ fontSize: 88 }}>
            {fmtInt(k.nok)}
          </div>
          <div className="foot">{fmtPct(k.shiftRate)} del turno</div>
        </div>
        <div className="lp-panel lp-tile" style={{ justifyContent: "center", gap: 10 }}>
          <div className="lbl">Estado</div>
          <div style={{ fontSize: 44, fontWeight: 700, lineHeight: 1.05 }}>
            Sin acciones
            <br />
            pendientes
          </div>
        </div>
      </section>
      <Panel title="Vigilancia · qué tan cerca está cada regla de pedir acción" aside={`Vigilando ${rules.length} reglas`}>
        <div className="lp-rules">
          {rules.map((rule) => (
            <div key={rule.code} className="lp-rule">
              <div>
                <div className="nm">
                  <span className="lp-num lp-muted" style={{ fontSize: 16, marginRight: 10 }}>
                    {rule.code}
                  </span>
                  {rule.name}
                </div>
                <div className="cons">{rule.cons}</div>
              </div>
              <div style={{ paddingTop: 22 }}>{rule.meter}</div>
              <div className="rv">
                <div className="big">{rule.big}</div>
                <div className="sm">{rule.sm}</div>
              </div>
            </div>
          ))}
        </div>
      </Panel>
      <Panel title="Últimas 90 piezas" aside={<StripLegend />}>
        <div className="lp-pb" style={{ paddingTop: 14 }}>
          <PieceStrip r={r} idx={idx} count={90} height={70} labels />
          <div className="lp-axis">
            <span>hace 90 pzs</span>
            <span>ahora →</span>
          </div>
        </div>
      </Panel>
    </main>
  );
}

export function GuidedResponseView(view: PanelView) {
  const { r, idx, k, alarms, session, onAction } = view;
  const ops = operatorAlarms(alarms);
  const a = ops[0];
  if (!a) return <CalmView {...view} />;
  const ev = a.ev;
  const contain = ev.rule === "R1" && session.stopped;
  const others = ops.filter((x) => x !== a);
  const st = stationName(r, ev.station);
  const timeline = shiftLog(r, idx, session, 12)
    .filter((l) => l.ts >= ev.evidence_from_ts - 0.5)
    .reverse()
    .slice(-5);
  const hindsight = ev.rule === "R1" && ev.cleared_index !== null && ev.cleared_index <= idx && ev.peak > r.rules.run_limit;
  return (
    <main className="lp-main lp-C alarm">
      <section className="lp-kstrip">
        <div className="lp-panel lp-kmini">
          <div className="lp-label">Producidas</div>
          <div className="val">{fmtInt(k.pieces)}</div>
        </div>
        <div className="lp-panel lp-kmini">
          <div className="lp-label">OK</div>
          <div className="val">{fmtInt(k.ok)}</div>
        </div>
        <div className="lp-panel lp-kmini">
          <div className="lp-label">NOK</div>
          <div className="val">{fmtInt(k.nok)}</div>
        </div>
        <div className="lp-panel lp-kmini">
          <div className="lp-label">NOK últimas {r.rules.rate_window}</div>
          <div className="val">
            {k.windowRate === null ? "—" : (k.windowRate * 100).toFixed(1)}
            <small>%</small>
          </div>
        </div>
        <div className="lp-panel lp-kmini" style={{ fontSize: 17 }}>
          {others.length ? (
            <>
              <div className="lp-label">También activas</div>
              {others.slice(0, 2).map((o) => (
                <div key={o.ev.id} style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 6, fontWeight: 600 }}>
                  <LpSymbol priority={o.ev.priority} size={20} blinking={!o.acked} />
                  {o.ev.rule} · {RULE_TITLE[o.ev.rule](o.ev)}
                </div>
              ))}
            </>
          ) : (
            <>
              <div className="lp-label">Avisos</div>
              <div style={{ marginTop: 6 }}>
                {advisorySummary(advisories(alarms))}
              </div>
            </>
          )}
        </div>
      </section>
      <section className="lp-Cmain">
        <section className="lp-panel">
          <div className={clsx("lp-band", contain ? "contain" : `p${ev.priority}`)} role="alert">
            <div style={contain ? { color: "var(--status-nok)" } : undefined}>
              <LpSymbol priority={ev.priority} size={100} onFill={!contain} blinking={!a.acked && !contain} />
            </div>
            <div style={{ minWidth: 0 }}>
              <div className="ttl">{contain ? "LÍNEA DETENIDA" : RULE_TITLE[ev.rule](ev)}</div>
              <div className="sub">
                {contain ? "Contención en curso · " : ""}
                {ev.rule} · {whatText(r, ev, idx)}
              </div>
            </div>
            <AlarmTimer a={a} r={r} idx={idx} />
          </div>
          <div className="lp-facts">
            <div className="lp-fact">
              <div className="lp-label">Qué pasó</div>
              <div className="v">
                {ev.rule === "R1"
                  ? `${ev.nests.length || r.rules.run_limit} NOK seguidas`
                  : ev.rule === "R2"
                    ? `Nido ${ev.key} a ${fmtRatio(idx >= 0 ? (r.state.nest_ratio_nest[idx] === ev.key ? r.state.nest_ratio[idx] : ev.value) : ev.value)}`
                    : fmtPct(k.windowRate)}
              </div>
            </div>
            <div className="lp-fact">
              <div className="lp-label">Dónde</div>
              <div className="v">
                {ev.rule === "R1" ? (ev.nests.length ? `Nidos ${distinctNests(ev).join(", ")}` : "Línea") : ev.rule === "R2" ? `Nido ${ev.key}` : "Toda la línea"}
                {st && (
                  <>
                    <br />
                    <span className="lp-muted" style={{ fontSize: 18, fontWeight: 500 }}>
                      {st}
                    </span>
                  </>
                )}
              </div>
            </div>
            <div className="lp-fact">
              <div className="lp-label">{ev.rule === "R1" ? "Segregar desde" : "Desde"}</div>
              <div className="v lp-num" style={{ fontSize: 28 }}>
                {plantClock(ev.rule === "R1" ? ev.evidence_from_ts : ev.raised_ts, r.utc_offset_minutes)}
              </div>
            </div>
            <div className="lp-fact">
              <div className="lp-label">{ev.rule === "R1" ? "Piezas a contención" : "Piezas desde la alarma"}</div>
              <div className="v lp-num" style={{ fontSize: 28 }}>
                {fmtInt(ev.rule === "R1" ? piecesToContain(ev, idx) : Math.max(0, idx - ev.raised_index))}
              </div>
            </div>
          </div>
          <div className="lp-evid">
            <div style={{ display: "flex", alignItems: "center", marginBottom: 12 }}>
              <span className="lp-label">
                {ev.rule === "R2"
                  ? `Evidencia · últimas ${r.rules.nest_window} piezas del nido ${ev.key}`
                  : "Evidencia · últimas 48 piezas (número = nido)"}
              </span>
              <span style={{ marginLeft: "auto" }}>
                <StripLegend />
              </span>
            </div>
            {ev.rule === "R2" && ev.key !== null ? (
              <PieceStrip r={r} idx={idx} count={r.rules.nest_window} height={110} nest={ev.key} />
            ) : (
              <PieceStrip r={r} idx={idx} count={48} height={110} labels />
            )}
            <div className="lp-axis">
              <span>{ev.rule === "R2" ? `hace ${r.rules.nest_window} pzs del nido` : "hace 48 pzs"}</span>
              <span>ahora →</span>
            </div>
            <div style={{ marginTop: 16 }}>
              <div className="lp-label" style={{ marginBottom: 8 }}>
                Cronología
              </div>
              <ul className="lp-log" style={{ fontSize: 17, gap: 6 }}>
                {ev.rule === "R1" && (
                  <li style={{ gridTemplateColumns: "96px 1fr" }}>
                    <span className="tm">{plantClock(ev.evidence_from_ts, r.utc_offset_minutes)}</span>
                    <span>Primera NOK de la racha</span>
                  </li>
                )}
                {timeline.map((l, i) => (
                  <li key={`${l.ts}-${i}`} style={{ gridTemplateColumns: "96px 1fr" }}>
                    <span className="tm">{plantClock(l.ts, r.utc_offset_minutes)}</span>
                    <span>{l.text}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="lp-why">
              <b>Por qué esta acción:</b> {whyText(r, ev)}
              {hindsight && (
                <>
                  {" "}
                  <b>Repetición:</b> en el histórico esta racha llegó a {fmtInt(ev.peak)} NOK seguidas (en vivo no se sabría).
                </>
              )}
            </div>
          </div>
        </section>
        <Panel
          title={`Respuesta · paso ${currentStep(a.done) + 1} de 4`}
          aside={
            <>
              <span className="lp-kbd">A</span>&nbsp; registrar acción
            </>
          }
        >
          <div className="lp-pb" style={{ display: "flex", flexDirection: "column", gap: 18 }}>
            <StepList items={steps(r, ev, idx)} done={a.done} size={23} />
            <div>
              <div className="lp-label" style={{ marginBottom: 10 }}>
                Registrar con un toque
              </div>
              <div className="lp-opts">
                {actionOptions(r, ev, idx).map((o, i) => (
                  <button key={o.label} type="button" className="lp-btn" onClick={() => onAction(ev, i)}>
                    <kbd>{i + 1}</kbd>
                    {o.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="lp-escbox">
              {a.acked ? (
                <span>
                  Reconocida a las <b className="lp-num">{plantClock(a.ackTs ?? ev.raised_ts, r.utc_offset_minutes)}</b>
                  {a.escalatedQuality ? " · escalada a calidad" : ""}
                </span>
              ) : (
                <>
                  <LpSymbol priority={ev.priority} size={26} blinking />
                  <span>
                    {a.escalated ? (
                      <b>Escalada a supervisor de turno</b>
                    ) : (
                      <>
                        Si nadie reconoce, escala a supervisor en <b className="lp-num">{mmss(escalationLeft(a))}</b>
                      </>
                    )}
                  </span>
                  <span style={{ marginLeft: "auto" }}>
                    <span className="lp-kbd">R</span> reconocer
                  </span>
                </>
              )}
            </div>
          </div>
        </Panel>
      </section>
    </main>
  );
}
