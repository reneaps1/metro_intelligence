import clsx from "clsx";
import {
  currentStep,
  fmtInt,
  fmtPct,
  fmtRatio,
  nestProgress,
  nestWindows,
  operatorAlarms,
  advisories,
  piecesToContain,
  RULE_TITLE,
  steps,
  streakAt,
  whatText,
  whereText,
} from "../../../lib/line-panel/model";
import { AlarmTimer, Bullet, LpSymbol, Panel, PieceStrip, StepList, StreakMeter, StripLegend, type PanelView } from "../parts";

// View A — Andon: read from 5–10 m. One status band, four KPIs, the last 60
// pieces with the streak meter, and the action the line has to take now.
export function AndonView(view: PanelView) {
  const { r, idx, k, alarms, session } = view;
  const ops = operatorAlarms(alarms);
  const a = ops[0];
  const ref = r.rules.reference_nok_rate;
  const r1 = a?.ev.rule === "R1" ? a : undefined;

  let banner;
  if (!a) {
    const top = [...nestWindows(r, idx).nests].sort((x, y) => (y.rate ?? 0) - (x.rate ?? 0))[0];
    banner = (
      <section className="lp-banner">
        <div>
          <div className="ttl">PRODUCCIÓN NORMAL</div>
          <div className="sub">
            Sin acciones pendientes · racha NOK {streakAt(r, idx)} de {r.rules.run_limit}
            {top && top.rate !== null && ` · nido más alto: ${top.nest} (${fmtPct(top.rate)})`} · últimas{" "}
            {r.rules.rate_window}: {fmtPct(k.windowRate)}
          </div>
        </div>
      </section>
    );
  } else {
    const contain = a.ev.rule === "R1" && session.stopped;
    const more = ops.length > 1 ? ` · +${ops.length - 1} alarma(s) más` : "";
    const next = steps(r, a.ev, idx)[currentStep(a.done)];
    banner = (
      <section className={clsx("lp-banner", contain ? "contain" : `p${a.ev.priority}`)} role="alert">
        <div style={contain ? { color: "var(--status-nok)" } : undefined}>
          <LpSymbol priority={a.ev.priority} size={contain ? 104 : 120} onFill={!contain} blinking={!a.acked} />
        </div>
        <div style={{ minWidth: 0 }}>
          <div className="ttl">{contain ? "LÍNEA DETENIDA · CONTENCIÓN" : RULE_TITLE[a.ev.rule](a.ev)}</div>
          <div className="sub">
            {whatText(r, a.ev, idx)} · {whereText(r, a.ev)}
            {more}
          </div>
          <div className="sub2">→ {next}</div>
        </div>
        <AlarmTimer a={a} r={r} idx={idx} />
      </section>
    );
  }

  const np = nestProgress(r, idx);
  const watch: [string, string, string, string][] = [
    ["R1", "Racha NOK consecutiva", `${streakAt(r, idx)} / ${r.rules.run_limit}`, "Parar línea"],
    [
      "R2",
      `Nido vs. resto (últ. ${r.rules.nest_window})`,
      np ? `N${np.nest} ${fmtRatio(np.ratio)} · ${np.nok}/${r.rules.nest_min_nok} NOK` : "—",
      "Revisar nido",
    ],
    ["R3", `NOK últimas ${r.rules.rate_window}`, `${fmtPct(k.windowRate)} / ${fmtPct(r.rules.rate_limit, 0)}`, "Avisar a calidad"],
  ];
  if (r.line.mold_cavities) {
    const adv = [...advisories(alarms)].sort((x, y) => y.ev.value - x.ev.value);
    const names = adv.slice(0, 3).map((x) => `C${x.ev.key}`).join(" · ");
    watch.push(["R4", "Cavidad de molde", adv.length > 3 ? `${names} +${adv.length - 3}` : names || "—", "Aviso herramental"]);
  }

  return (
    <main className="lp-main lp-A">
      {banner}
      <section className="lp-kpis4">
        <div className="lp-panel lp-tile">
          <div className="lbl">Piezas producidas</div>
          <div className="val">{fmtInt(k.pieces)}</div>
          <div className="foot">
            Ritmo <b className="lp-num">{fmtInt(k.piecesPerHour)}</b> pzs/h · turno {view.counts.shift?.label ?? "—"}
          </div>
        </div>
        <div className="lp-panel lp-tile">
          <div className="lbl">Cantidad OK</div>
          <div className="val">{fmtInt(k.ok)}</div>
          <div className="foot">
            <b className="lp-num">{fmtPct(k.pieces ? k.ok / k.pieces : null)}</b> del turno
          </div>
        </div>
        <div className={clsx("lp-panel lp-tile", r1 && "alarm")}>
          <div className="lbl">Cantidad NOK</div>
          <div className="val">{fmtInt(k.nok)}</div>
          <div className="foot">
            {r1 ? (
              <>
                <b className="lp-num">{fmtInt(piecesToContain(r1.ev, idx))}</b> pzs a contención
              </>
            ) : (
              <>
                <b className="lp-num">{fmtInt(k.windowNok)}</b> en las últimas {r.rules.rate_window}
              </>
            )}
          </div>
        </div>
        <div className="lp-panel lp-tile">
          <div className="lbl">% NOK turno</div>
          <div className="val">
            {k.shiftRate === null ? "—" : (k.shiftRate * 100).toLocaleString("es-MX", { maximumFractionDigits: 1, minimumFractionDigits: 1 })}
            <small>%</small>
          </div>
          <div>
            <div className="foot">
              Últimas {r.rules.rate_window}: <b className="lp-num">{fmtPct(k.windowRate)}</b>
              <span style={{ fontSize: 15 }}>
                {" "}
                · ref. {fmtPct(ref)} · alarma {fmtPct(r.rules.rate_limit, 0)}
              </span>
            </div>
            <Bullet value={k.windowRate} max={Math.max(r.rules.rate_limit * 2, 0.05)} reference={ref} limit={r.rules.rate_limit} />
          </div>
        </div>
      </section>
      <section className="lp-A-bottom">
        <Panel title="Últimas 60 piezas" aside={<StripLegend />}>
          <div className="lp-pb" style={{ display: "flex", flexDirection: "column", gap: 18 }}>
            <div>
              <PieceStrip r={r} idx={idx} count={60} height={112} />
              <div className="lp-axis">
                <span>hace 60 pzs</span>
                <span>ahora →</span>
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 28 }}>
              <div className="lp-label" style={{ fontSize: 16, width: 150 }}>
                Racha NOK actual
              </div>
              <StreakMeter r={r} idx={idx} alarms={alarms} />
            </div>
          </div>
        </Panel>
        <Panel
          title={a ? `Acción requerida · ${a.ev.rule}` : "Acción requerida"}
          aside={
            a && (
              <>
                <span className="lp-kbd">A</span>&nbsp; registrar
              </>
            )
          }
        >
          <div className="lp-pb">
            {a ? (
              <StepList items={steps(r, a.ev, idx)} done={a.done} size={20} />
            ) : (
              <>
                <div style={{ fontSize: 26, fontWeight: 600, marginBottom: 14 }}>Ninguna · continuar producción</div>
                <div className="lp-watch">
                  {watch.map(([code, name, v, act]) => (
                    <div key={code} style={{ display: "contents" }}>
                      <span className="code">{code}</span>
                      <span>
                        {name} <span className="lp-muted">→ {act}</span>
                      </span>
                      <span className="v">{v}</span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </Panel>
      </section>
    </main>
  );
}

