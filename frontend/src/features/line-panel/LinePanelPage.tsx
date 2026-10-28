import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { OriginBadge } from "../../components/ui/OriginBadge";
import { DEMO_BASE_PATH } from "../../lib/demo/steps";
import { fetchLineMoments, fetchLineReplay } from "../../lib/line-panel/api";
import {
  activeAlarms,
  emptySession,
  indexAt,
  kpis,
  operatorAlarms,
  piecesToContain,
  pieceTs,
  plantClock,
  sessionReducer,
  shiftCounts,
} from "../../lib/line-panel/model";
import type { LineAlarmEvent, LineMoment, LineMoments, LineReplay, MomentKind } from "../../lib/line-panel/types";
import { fetchDatasets } from "../../lib/quality-analytics/api";
import { useTheme } from "../../lib/theme/ThemeProvider";
import { ActionDialog, type PanelView } from "./parts";
import { AndonView } from "./views/AndonView";
import { GuidedResponseView } from "./views/GuidedResponseView";
import { ProcessMapView } from "./views/ProcessMapView";
import "./linePanel.css";

// IQ-F15: full-screen line quality panel (docs/design/line-quality-panel.md).
// Replays the active dimensional dataset piece by piece; the backend engine
// decides when each rule fires, the operator's acknowledgements and actions
// are session state only.

type ViewId = "A" | "B" | "C";
const VIEW_NAMES: Record<ViewId, string> = { A: "Andon de línea", B: "Mapa de proceso", C: "Respuesta guiada" };
const SPEEDS = [1, 5, 20];
const REAL_ID = "real-dimensional";
const SYNTHETIC_ID = "demo-synthetic-dimensional";
/** Replay seconds shown before a stop / attention event when the presenter jumps to it. */
const PREROLL_S = 15;
const KIND_LABEL: Record<MomentKind, string> = { normal: "Normal", attention: "Atención", stop: "Paro" };

function isTyping(target: EventTarget | null) {
  const el = target as HTMLElement | null;
  return !!el && (el.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName));
}

export function LinePanelPage() {
  const { resolvedTheme, setPreference } = useTheme();
  const [dataset, setDataset] = useState<string | null>(null);
  const [moments, setMoments] = useState<LineMoments | null>(null);
  const [replay, setReplay] = useState<LineReplay | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<ViewId>("A");
  const [kind, setKind] = useState<MomentKind | null>(null);
  const [cycle, setCycle] = useState<Record<MomentKind, number>>({ normal: 0, attention: 0, stop: 0 });
  const [t, setT] = useState(0);
  const [paused, setPaused] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [dialog, setDialog] = useState(false);
  const [help, setHelp] = useState(false);
  const [proto, setProto] = useState(true);
  const [scale, setScale] = useState(1);
  const [session, dispatch] = useReducer(sessionReducer, undefined, emptySession);
  const hideTimer = useRef<number>();

  // Dataset: the local REAL one when the backend has it, otherwise the synthetic one.
  useEffect(() => {
    fetchDatasets()
      .then(({ items }) => setDataset(items.some((d) => d.id === REAL_ID) ? REAL_ID : SYNTHETIC_ID))
      .catch(() => setDataset(SYNTHETIC_ID));
  }, []);

  const load = useCallback(
    async (start: number, label: string, keepSession = false, focusTs?: number) => {
      if (!dataset) return;
      setLoading(true);
      setError(null);
      try {
        const r = await fetchLineReplay({ dataset, start });
        // A presenter jump lands a few seconds before the event, with the strips already full.
        const t0 = focusTs === undefined ? 0 : Math.max(0, focusTs - r.window.start_ts - PREROLL_S);
        setReplay(r);
        setT(t0);
        setPaused(false);
        if (!keepSession) {
          const from = r.window.start_ts + t0;
          dispatch({
            type: "reset",
            ts: from,
            text: `Repetición desde ${plantClock(from, r.utc_offset_minutes)} · ${label}`,
            inheritBefore: from,
          });
        }
      } catch {
        setError("No se pudo cargar la repetición. Revisa la conexión con el servidor y vuelve a intentar.");
      } finally {
        setLoading(false);
      }
    },
    [dataset],
  );

  const goTo = useCallback(
    (m: LineMoment | null, all: LineMoments) => {
      setKind(m?.kind ?? null);
      const focus = m && m.kind !== "normal" ? m.raised_ts : undefined;
      void load(m ? m.replay_start_ts : all.start_ts, m ? m.label : "inicio de los datos", false, focus);
    },
    [load],
  );

  useEffect(() => {
    if (!dataset) return;
    fetchLineMoments(dataset)
      .then((m) => {
        setMoments(m);
        const first = m.moments.find((x) => x.kind === "normal") ?? m.moments[0] ?? null;
        goTo(first, m);
      })
      .catch(() => {
        setLoading(false);
        setError("No se pudieron cargar los momentos de la línea. Vuelve a intentar.");
      });
  }, [dataset, goTo]);

  const jump = useCallback(
    (k: MomentKind) => {
      if (!moments) return;
      const list = moments.moments.filter((m) => m.kind === k);
      if (!list.length) return;
      const i = cycle[k] % list.length;
      setCycle((c) => ({ ...c, [k]: c[k] + 1 }));
      goTo(list[i], moments);
    },
    [moments, cycle, goTo],
  );

  // Replay clock: replay seconds advance with real time × speed; a stopped line pauses it.
  const running = !!replay && !paused && !session.stopped && !loading;
  useEffect(() => {
    if (!running || !replay) return;
    let last = performance.now();
    const id = window.setInterval(() => {
      const now = performance.now();
      const dt = Math.min(1, (now - last) / 1000);
      last = now;
      setT((x) => x + dt * speed);
    }, 250);
    return () => window.clearInterval(id);
  }, [running, replay, speed]);

  // End of the window: continue with the next one, keeping the operator session.
  useEffect(() => {
    if (!replay || loading) return;
    if (t >= replay.window.end_ts - replay.window.start_ts && moments && replay.window.end_ts < moments.end_ts) {
      void load(replay.window.end_ts, "continuación", true);
    }
  }, [t, replay, loading, moments, load]);

  const idx = replay ? indexAt(replay, t) : -1;
  const derived = useMemo(() => {
    if (!replay) return null;
    const counts = shiftCounts(replay, idx);
    return { counts, k: kpis(replay, idx, counts), alarms: activeAlarms(replay, idx, session) };
  }, [replay, idx, session]);

  const nowTs = replay && idx >= 0 ? pieceTs(replay, idx) : (replay?.window.start_ts ?? 0);
  const ops = derived ? operatorAlarms(derived.alarms) : [];
  const top = ops[0];

  const onAction = useCallback(
    (alarm: LineAlarmEvent, option: number) => {
      if (!replay) return;
      dispatch({ type: "act", alarm, option, ts: nowTs, contained: piecesToContain(alarm, idx) });
    },
    [replay, nowTs, idx],
  );

  const acknowledge = useCallback(() => {
    const a = ops.find((x) => !x.acked);
    if (a) dispatch({ type: "ack", id: a.ev.id, ts: nowTs });
  }, [ops, nowTs]);

  const toggleFullscreen = useCallback(() => {
    const done = document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen?.();
    Promise.resolve(done).catch(() => undefined);
  }, []);

  const showProto = useCallback(() => {
    setProto(true);
    window.clearTimeout(hideTimer.current);
    hideTimer.current = window.setTimeout(() => setProto(false), 3500);
  }, []);

  useEffect(() => {
    showProto();
    return () => window.clearTimeout(hideTimer.current);
  }, [showProto]);

  useEffect(() => {
    const fit = () => setScale(Math.min(window.innerWidth / 1920, window.innerHeight / 1080));
    fit();
    window.addEventListener("resize", fit);
    return () => window.removeEventListener("resize", fit);
  }, []);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.ctrlKey || e.metaKey || e.altKey || isTyping(e.target)) return;
      const key = e.key.toLowerCase();
      if (dialog) {
        if ("1234".includes(key) && key.length === 1 && top) {
          onAction(top.ev, Number(key) - 1);
          setDialog(false);
        } else if (key === "escape") setDialog(false);
        else return;
        e.preventDefault();
        return;
      }
      const actions: Record<string, () => void> = {
        r: acknowledge,
        a: () => top && setDialog(true),
        f: toggleFullscreen,
        "1": () => setView("A"),
        "2": () => setView("B"),
        "3": () => setView("C"),
        n: () => jump("normal"),
        w: () => jump("attention"),
        s: () => jump("stop"),
        " ": () => setPaused((p) => !p),
        v: () => setSpeed((s) => SPEEDS[(SPEEDS.indexOf(s) + 1) % SPEEDS.length]),
        d: () => setPreference(resolvedTheme === "dark" ? "light" : "dark"),
        h: () => setHelp((h) => !h),
        "?": () => setHelp((h) => !h),
        escape: () => setHelp(false),
      };
      const fn = actions[key];
      if (!fn) return;
      e.preventDefault();
      fn();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [dialog, top, onAction, acknowledge, toggleFullscreen, jump, resolvedTheme, setPreference]);

  const counts = derived?.counts;
  const panelView: PanelView | null =
    replay && derived ? { r: replay, idx, counts: derived.counts, k: derived.k, alarms: derived.alarms, session, onAction } : null;
  const hasKind = (k: MomentKind) => !!moments?.moments.some((m) => m.kind === k);
  const date = replay ? new Date((nowTs + replay.utc_offset_minutes * 60) * 1000).toISOString().slice(0, 10) : "";

  return (
    <div className="wb-root lp-root" onMouseMove={showProto} onTouchStart={showProto}>
      <nav className={proto ? "lp-proto" : "lp-proto hide"} aria-label="Controles del presentador">
        <span className="pl">Presentador</span>
        {(["A", "B", "C"] as ViewId[]).map((v, i) => (
          <button key={v} type="button" aria-pressed={view === v} onClick={() => setView(v)}>
            <kbd>{i + 1}</kbd>
            {v} · {VIEW_NAMES[v]}
          </button>
        ))}
        <span className="dv" />
        {(["normal", "attention", "stop"] as MomentKind[]).map((k) => (
          <button
            key={k}
            type="button"
            aria-pressed={kind === k}
            disabled={!hasKind(k)}
            title={hasKind(k) ? `Ir al siguiente momento real de tipo ${KIND_LABEL[k].toLowerCase()}` : "No hay momentos de este tipo en el dataset"}
            onClick={() => jump(k)}
          >
            <kbd>{k === "normal" ? "N" : k === "attention" ? "W" : "S"}</kbd>
            {KIND_LABEL[k]}
          </button>
        ))}
        <span className="dv" />
        <button type="button" onClick={() => setPaused((p) => !p)} aria-pressed={paused}>
          <kbd>␣</kbd>
          {paused ? "Reanudar" : "Pausa"}
        </button>
        <button type="button" onClick={() => setSpeed((s) => SPEEDS[(SPEEDS.indexOf(s) + 1) % SPEEDS.length])}>
          <kbd>V</kbd>×{speed}
        </button>
        <button type="button" onClick={() => setPreference(resolvedTheme === "dark" ? "light" : "dark")}>
          <kbd>D</kbd>Tema
        </button>
        <button type="button" onClick={() => setHelp(true)}>
          <kbd>?</kbd>Ayuda
        </button>
        <Link to={DEMO_BASE_PATH}>← Banco de trabajo</Link>
      </nav>

      <div className="lp-stage" style={{ ["--lp-k" as string]: scale }} aria-live="polite">
        <header className="lp-top">
          <div className="lp-brand">
            <span className="lp-mark">MI</span>
            <div>
              <div className="t1">Calidad en línea</div>
              <div className="t2">Metro Intelligence · Edición industrial</div>
            </div>
          </div>
          <div className="lp-ctx">
            <span>
              <b>{replay?.machine ?? "Línea"}</b> Inyección + inspección
            </span>
            <span>{replay?.dataset_name}</span>
            <span>
              Turno <b>{counts?.shift?.label ?? "—"}</b>
            </span>
          </div>
          <div className="right">
            {session.stopped ? (
              <span className="lp-chip stop">
                <span className="dot" />
                Línea detenida
              </span>
            ) : (
              <span className="lp-chip">
                <span className="dot" />
                {paused ? "Repetición en pausa" : "En producción"}
              </span>
            )}
            {replay && <OriginBadge origin={replay.provenance} />}
            <span className="lp-clock lp-num">{replay ? plantClock(nowTs, replay.utc_offset_minutes) : "--:--:--"}</span>
          </div>
        </header>

        {panelView ? (
          view === "A" ? (
            <AndonView {...panelView} />
          ) : view === "B" ? (
            <ProcessMapView {...panelView} />
          ) : (
            <GuidedResponseView {...panelView} />
          )
        ) : (
          <main className="lp-main" style={{ position: "relative" }}>
            <div className="lp-center">
              {error ? (
                <div>
                  <p>{error}</p>
                  <button type="button" className="lp-btn" onClick={() => moments && goTo(null, moments)}>
                    Reintentar
                  </button>
                </div>
              ) : (
                "Cargando la repetición de la línea…"
              )}
            </div>
          </main>
        )}

        <nav className="lp-cmds" aria-label="Comandos">
          <button type="button" className={ops.some((x) => !x.acked) ? "lp-btn primary" : "lp-btn"} disabled={!ops.some((x) => !x.acked)} onClick={acknowledge}>
            <kbd>R</kbd>Reconocer
          </button>
          <button type="button" className={top ? "lp-btn primary" : "lp-btn"} disabled={!top} onClick={() => setDialog(true)}>
            <kbd>A</kbd>Registrar acción
          </button>
          <button type="button" className="lp-btn" onClick={toggleFullscreen}>
            <kbd>F</kbd>Pantalla completa
          </button>
          <span className="note">El panel pide la acción; el paro y las decisiones los ejecuta el operador.</span>
        </nav>
        <footer className="lp-status">
          <span>
            Repetición · {date} · ×{speed}
            {paused ? " · en pausa" : ""}
          </span>
          {replay && (
            <span>
              Motor {replay.engine_name} {replay.engine_version} · reglas relativas a la ref. histórica de la línea
            </span>
          )}
          <span>Turnos de 8 h desde las 06:00 (supuesto de la demo)</span>
          <span className="r">
            Vista {view} · {VIEW_NAMES[view]}
          </span>
        </footer>

        {dialog && panelView && top && <ActionDialog view={panelView} alarm={top} onClose={() => setDialog(false)} />}
      </div>

      {help && (
        <div className="lp-scrim" style={{ position: "fixed", zIndex: 30 }} onClick={() => setHelp(false)}>
          <div className="lp-dlg" role="dialog" aria-modal="true" aria-label="Comandos del panel" style={{ width: "min(680px, calc(100vw - 32px))", padding: "20px 28px", fontSize: 15, lineHeight: 1.5 }}>
            <h2 style={{ margin: "0 0 10px", fontSize: 20 }}>Comandos del panel</h2>
            <p style={{ margin: "4px 0" }}>
              <b>R</b> reconocer la alarma de mayor prioridad · <b>A</b> registrar acción (1–4, Esc cancela) · <b>F</b> pantalla completa
            </p>
            <p style={{ margin: "4px 0" }}>
              <b>1 · 2 · 3</b> vista Andon / Mapa de proceso / Respuesta guiada
            </p>
            <p style={{ margin: "4px 0" }}>
              <b>N · W · S</b> saltar al siguiente momento real normal / de atención / de paro del histórico ·{" "}
              <b>Espacio</b> pausa · <b>V</b> velocidad ×1/×5/×20 · <b>D</b> tema
            </p>
            <p style={{ margin: "10px 0 0", color: "var(--text-secondary)" }}>
              Repetición pieza por pieza de los datos de la línea. Las alarmas las decide el motor de reglas del servidor; los
              reconocimientos y acciones de esta pantalla no se guardan.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
