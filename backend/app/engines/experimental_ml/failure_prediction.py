"""IQ-F7.b: EXPERIMENTAL machine-failure prediction study on SIMULATED data.

Pure engine (CLAUDE.md §3): no DB/IO. It reads the simulated hourly history
from ``app.engines.process_simulation.failure_history`` and runs a small,
fully explainable study:

1. Features at hour ``t`` use ONLY data at hours ``<= t`` (``features_at``).
   The label -- "a failure occurs in hours ``(t, t + HORIZON_H]``" -- is never
   a feature.
2. Temporal split over an unseen period: train on the first ``TRAIN_WEEKS``
   weeks of every machine, test on the remaining weeks. Train rows whose label
   window would reach into the test period are dropped, and standardization
   uses train statistics only.
3. L2-regularized logistic regression fitted in pure Python (Newton/IRLS).
4. Honest evaluation on the test rows: confusion matrix and precision/recall
   per threshold, PR-AUC, per-episode anticipation and lead time, debounced
   false-alarm events per 8 h shift -- all compared against two baselines
   evaluated on exactly the same test rows.

``ENGINE_VERSION``'s "-experimental" suffix must never be dropped: this is a
shadow-mode study for a demo, it never writes an Alert/Recommendation and
never acts on any machine (CLAUDE.md §2, §16).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache

from app.engines.process_simulation.failure_history import (
    HOURS_PER_WEEK,
    MACHINES,
    FailureEvent,
    FailureHistory,
    simulate_history,
)

ENGINE_NAME = "failure_prediction_engine"
ENGINE_VERSION = "v1-experimental"  # never drop "-experimental": shadow-mode study only.

HORIZON_H = 6
FIRST_ROW_H = 24
TRAIN_WEEKS = 6
TEST_START_H = TRAIN_WEEKS * HOURS_PER_WEEK
HOURS_CAP = 168.0
L2 = 1.0
MAX_ITERATIONS = 30
LOGIT_CLIP = 30.0
SHIFT_H = 8.0
THRESHOLDS: tuple[float, ...] = tuple(round(0.05 * i, 2) for i in range(1, 20))
DEFAULT_THRESHOLD = 0.5

FEATURES: tuple[tuple[str, str], ...] = (
    ("failures_1h", "Fallas en la última hora"),
    ("failures_8h", "Fallas en las últimas 8 h"),
    ("failures_24h", "Fallas en las últimas 24 h"),
    ("alarms_1h", "Alarmas menores en la última hora"),
    ("alarms_8h", "Alarmas menores en las últimas 8 h"),
    ("alarms_24h", "Alarmas menores en las últimas 24 h"),
    ("hours_since_failure", "Horas desde la última falla"),
    ("hours_since_maintenance", "Horas desde el último mantenimiento"),
    ("vib_mean_2h", "Vibración media (2 h)"),
    ("vib_slope", "Tendencia de vibración (3 h)"),
    ("current_slope", "Tendencia de corriente (3 h)"),
)

LIMITATIONS: tuple[str, ...] = (
    "Datos 100 % simulados: el historial de fallas, vibración, corriente y alarmas es ficticio "
    "y no representa ninguna planta ni máquina real.",
    "El modelo solo anticipa fallas que tienen precursores físicos medibles; las fallas sin "
    "precursor no son predecibles con estas señales.",
    "Para replicarlo en planta haría falta: historial de alarmas del PLC, registro de paros y "
    "mantenimientos con marca de tiempo, y etiquetado de la causa de cada falla.",
    "Un modelo así requiere validación prospectiva (en sombra, sobre periodos futuros) antes de "
    "usarse para priorizar intervenciones.",
    "Nunca actúa automáticamente sobre la máquina: solo genera alertas para que una persona "
    "autorizada decida.",
)


@dataclass(frozen=True)
class LogisticModel:
    """Fitted logistic regression.

    Attributes:
        intercept: Unpenalized intercept.
        coefficients: One coefficient per feature column.
        iterations: Newton iterations performed.
    """

    intercept: float
    coefficients: list[float]
    iterations: int


@dataclass(frozen=True)
class EpisodeEval:
    """Per-episode evaluation of a set of alert hours on one or more machines.

    Attributes:
        episodes_total: Failures evaluated.
        episodes_anticipated: Failures with an alert in ``[f - horizon, f)``.
        leads: Lead time (h) of each anticipated failure.
        false_alarm_events: Debounced alert runs with no failure shortly after.
        alert_events: Debounced alert runs (contiguous alert hours).
    """

    episodes_total: int
    episodes_anticipated: int
    leads: list[int]
    false_alarm_events: int
    alert_events: int


@dataclass(frozen=True)
class StudySplit:
    """Description and sizes of the temporal train/test split."""

    description: str
    train_rows: int
    test_rows: int
    train_failures: int
    test_failures: int
    test_positive_rate: float


@dataclass(frozen=True)
class FeatureWeight:
    """A model coefficient on the standardized feature scale."""

    key: str
    label: str
    coefficient: float


@dataclass(frozen=True)
class ThresholdRow:
    """Row-level and episode-level metrics at one alert threshold."""

    threshold: float
    tp: int
    fp: int
    fn: int
    tn: int
    precision: float | None
    recall: float
    episodes_total: int
    episodes_anticipated: int
    mean_lead_h: float | None
    false_alarms_per_shift: float
    alert_events: int


@dataclass(frozen=True)
class BaselineResult:
    """A naive baseline evaluated on the same test rows as the model."""

    key: str
    label: str
    pr_auc: float
    at_half: ThresholdRow


@dataclass(frozen=True)
class TimelinePoint:
    """One test hour of the showcased machine."""

    hour: int
    score: float
    vibration: float
    current: float
    alarms: int


@dataclass(frozen=True)
class StudyTimeline:
    """Model scores vs. simulated failures for one machine, test hours only."""

    machine: str
    points: list[TimelinePoint]
    failures: list[FailureEvent]
    maintenance_h: list[int]


@dataclass(frozen=True)
class PrecursorBreakdown:
    """Test failures anticipated at threshold 0.5, split by precursor presence."""

    with_precursor_total: int
    with_precursor_anticipated: int
    without_precursor_total: int
    without_precursor_anticipated: int


@dataclass(frozen=True)
class StudyResult:
    """Full output of the experimental failure-prediction study."""

    engine_name: str
    engine_version: str
    horizon_h: int
    split: StudySplit
    features: list[FeatureWeight]
    intercept: float
    model_pr_auc: float
    thresholds: list[ThresholdRow]
    baselines: list[BaselineResult]
    timeline: StudyTimeline
    precursor_breakdown: PrecursorBreakdown
    limitations: list[str]


# --------------------------------------------------------------------------- features


def _window_sum(values: Sequence[int], t: int, hours: int) -> int:
    """Sum of ``values`` over hours ``(t - hours, t]``."""
    return sum(values[max(0, t - hours + 1) : t + 1])


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _window_mean(values: Sequence[float], start: int, end: int) -> float:
    """Mean of ``values`` over hours ``[start, end]`` (clipped at 0)."""
    return _mean(values[max(0, start) : end + 1])


def features_at(history: FailureHistory, t: int) -> dict[str, float]:
    """Computes the feature vector at hour ``t`` from data at hours ``<= t`` only.

    Args:
        history: Simulated machine history.
        t: Hour index at which the prediction is made.

    Returns:
        Mapping from feature key (see ``FEATURES``) to value.
    """
    past_failures = [e.hour for e in history.failures if e.hour <= t]
    past_maintenance = [h for h in history.maintenance_h if h <= t]
    last_failure = max(past_failures) if past_failures else None
    last_maintenance = max(past_maintenance) if past_maintenance else None
    vib = history.vibration
    cur = history.current
    return {
        "failures_1h": float(sum(1 for f in past_failures if f > t - 1)),
        "failures_8h": float(sum(1 for f in past_failures if f > t - 8)),
        "failures_24h": float(sum(1 for f in past_failures if f > t - 24)),
        "alarms_1h": float(_window_sum(history.alarms, t, 1)),
        "alarms_8h": float(_window_sum(history.alarms, t, 8)),
        "alarms_24h": float(_window_sum(history.alarms, t, 24)),
        "hours_since_failure": HOURS_CAP if last_failure is None else min(HOURS_CAP, float(t - last_failure)),
        "hours_since_maintenance": (
            HOURS_CAP if last_maintenance is None else min(HOURS_CAP, float(t - last_maintenance))
        ),
        "vib_mean_2h": _window_mean(vib, t - 1, t),
        "vib_slope": _window_mean(vib, t - 2, t) - _window_mean(vib, t - 6, t - 4),
        "current_slope": _window_mean(cur, t - 2, t) - _window_mean(cur, t - 6, t - 4),
    }


def label_at(history: FailureHistory, t: int, horizon_h: int = HORIZON_H) -> int:
    """Label: 1 iff a failure occurs in hours ``(t, t + horizon_h]``."""
    return int(any(t < e.hour <= t + horizon_h for e in history.failures))


def _row_hours(history: FailureHistory) -> list[int]:
    """Every non-downtime hour from ``FIRST_ROW_H`` to ``hours - HORIZON_H - 1``."""
    return [t for t in range(FIRST_ROW_H, history.hours - HORIZON_H) if not history.downtime[t]]


# --------------------------------------------------------------------------- logistic regression


def _sigmoid(z: float) -> float:
    z = max(-LOGIT_CLIP, min(LOGIT_CLIP, z))
    return 1.0 / (1.0 + math.exp(-z))


def _solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    """Solves ``matrix @ x = vector`` by Gaussian elimination with partial pivoting."""
    n = len(vector)
    a = [row[:] + [vector[i]] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[pivot][col]) < 1e-12:
            raise ValueError("singular Hessian")
        a[col], a[pivot] = a[pivot], a[col]
        for r in range(col + 1, n):
            factor = a[r][col] / a[col][col]
            if factor:
                for c in range(col, n + 1):
                    a[r][c] -= factor * a[col][c]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        x[r] = (a[r][n] - sum(a[r][c] * x[c] for c in range(r + 1, n))) / a[r][r]
    return x


def fit_logistic(X: list[list[float]], y: list[int], l2: float) -> LogisticModel:  # noqa: N803
    """Fits an L2-regularized logistic regression by Newton/IRLS.

    The intercept is not penalized. The logit is clipped for numerical safety.

    Args:
        X: Feature rows (already scaled as desired).
        y: Binary labels (0/1), one per row.
        l2: L2 penalty strength on the coefficients.

    Returns:
        The fitted ``LogisticModel``.

    Raises:
        ValueError: If ``X`` is empty or ``X``/``y`` lengths differ.
    """
    if not X or len(X) != len(y):
        raise ValueError("X must be non-empty and match y in length")
    p = len(X[0])
    size = p + 1
    beta = [0.0] * size  # beta[0] is the intercept
    rows = [[1.0, *row] for row in X]
    iterations = 0
    for iterations in range(1, MAX_ITERATIONS + 1):  # noqa: B007
        gradient = [0.0] * size
        hessian = [[0.0] * size for _ in range(size)]
        for row, target in zip(rows, y, strict=True):
            prob = _sigmoid(sum(b * v for b, v in zip(beta, row, strict=True)))
            residual = target - prob
            weight = max(prob * (1.0 - prob), 1e-10)
            for i in range(size):
                ri = row[i]
                if ri == 0.0:
                    continue
                gradient[i] += residual * ri
                wri = weight * ri
                hrow = hessian[i]
                for j in range(i, size):
                    hrow[j] += wri * row[j]
        for i in range(1, size):
            gradient[i] -= l2 * beta[i]
            hessian[i][i] += l2
        for i in range(size):
            for j in range(i):
                hessian[i][j] = hessian[j][i]
        step = _solve(hessian, gradient)
        beta = [b + s for b, s in zip(beta, step, strict=True)]
        if max(abs(s) for s in step) < 1e-8:
            break
    return LogisticModel(intercept=beta[0], coefficients=beta[1:], iterations=iterations)


def predict_proba(model: LogisticModel, x: Sequence[float]) -> float:
    """Probability of the positive class for one feature row."""
    z = model.intercept + sum(c * v for c, v in zip(model.coefficients, x, strict=True))
    return _sigmoid(z)


# --------------------------------------------------------------------------- evaluation


def confusion(scores: Sequence[float], labels: Sequence[int], threshold: float) -> tuple[int, int, int, int]:
    """Confusion counts ``(tp, fp, fn, tn)``; a row alerts iff ``score >= threshold``."""
    tp = fp = fn = tn = 0
    for score, label in zip(scores, labels, strict=True):
        alert = score >= threshold
        if alert and label:
            tp += 1
        elif alert:
            fp += 1
        elif label:
            fn += 1
        else:
            tn += 1
    return tp, fp, fn, tn


def average_precision(scores: Sequence[float], labels: Sequence[int]) -> float:
    """Step-wise PR-AUC: ``sum((R_k - R_{k-1}) * P_k)`` over distinct score thresholds.

    Tied scores are treated as a single threshold. Returns 0.0 without positives.
    """
    positives = sum(labels)
    if positives == 0:
        return 0.0
    pairs = sorted(zip(scores, labels, strict=True), key=lambda pair: -pair[0])
    ap = 0.0
    tp = fp = 0
    previous_recall = 0.0
    i = 0
    while i < len(pairs):
        score = pairs[i][0]
        while i < len(pairs) and pairs[i][0] == score:
            if pairs[i][1]:
                tp += 1
            else:
                fp += 1
            i += 1
        recall = tp / positives
        ap += (recall - previous_recall) * (tp / (tp + fp))
        previous_recall = recall
    return ap


def _alert_runs(alert_hours: Sequence[int]) -> list[tuple[int, int]]:
    """Debounces alert hours into contiguous ``(start, end)`` runs."""
    runs: list[tuple[int, int]] = []
    for h in sorted(set(alert_hours)):
        if runs and h == runs[-1][1] + 1:
            runs[-1] = (runs[-1][0], h)
        else:
            runs.append((h, h))
    return runs


def _lead(alert_hours: Sequence[int], failure_hour: int, horizon_h: int) -> int | None:
    """Lead time of the first alert in ``[f - horizon_h, f)``, or ``None``."""
    window = [h for h in alert_hours if failure_hour - horizon_h <= h < failure_hour]
    return failure_hour - min(window) if window else None


def evaluate_episodes(alert_hours: list[int], failure_hours: list[int], horizon_h: int) -> EpisodeEval:
    """Per-episode evaluation of alerts against failures (one machine's hour axis).

    A failure ``f`` is anticipated if some alert hour is in ``[f - horizon_h, f)``;
    an alert at the failure hour or later does not count. Alert events are
    contiguous runs of alert hours; a run is a false alarm if no failure falls in
    ``(run_start, run_end + horizon_h]``.

    Args:
        alert_hours: Hours at which the alert was on.
        failure_hours: Hours of the failures to evaluate.
        horizon_h: Anticipation horizon in hours.

    Returns:
        The ``EpisodeEval`` summary.
    """
    leads = [lead for f in sorted(failure_hours) if (lead := _lead(alert_hours, f, horizon_h)) is not None]
    runs = _alert_runs(alert_hours)
    false_alarms = sum(
        1 for start, end in runs if not any(start < f <= end + horizon_h for f in failure_hours)
    )
    return EpisodeEval(
        episodes_total=len(failure_hours),
        episodes_anticipated=len(leads),
        leads=leads,
        false_alarm_events=false_alarms,
        alert_events=len(runs),
    )


# --------------------------------------------------------------------------- study


@dataclass(frozen=True)
class _MachineTest:
    machine: str
    hours: list[int]
    labels: list[int]
    episodes: list[FailureEvent]


def _test_episodes(history: FailureHistory, last_row_h: int) -> list[FailureEvent]:
    """Test failures whose whole anticipation window lies in the test period."""
    return [e for e in history.failures if TEST_START_H + HORIZON_H <= e.hour <= last_row_h + 1]


def _threshold_row(
    threshold: float, tests: list[_MachineTest], scores: list[list[float]], test_rows: int
) -> ThresholdRow:
    flat_scores = [s for machine_scores in scores for s in machine_scores]
    flat_labels = [label for test in tests for label in test.labels]
    tp, fp, fn, tn = confusion(flat_scores, flat_labels, threshold)
    total = anticipated = false_alarms = alert_events = 0
    leads: list[int] = []
    for test, machine_scores in zip(tests, scores, strict=True):
        alerts = [h for h, s in zip(test.hours, machine_scores, strict=True) if s >= threshold]
        result = evaluate_episodes(alerts, [e.hour for e in test.episodes], HORIZON_H)
        total += result.episodes_total
        anticipated += result.episodes_anticipated
        leads.extend(result.leads)
        false_alarms += result.false_alarm_events
        alert_events += result.alert_events
    return ThresholdRow(
        threshold=threshold,
        tp=tp,
        fp=fp,
        fn=fn,
        tn=tn,
        precision=tp / (tp + fp) if tp + fp else None,
        recall=tp / (tp + fn) if tp + fn else 0.0,
        episodes_total=total,
        episodes_anticipated=anticipated,
        mean_lead_h=sum(leads) / len(leads) if leads else None,
        false_alarms_per_shift=false_alarms / (test_rows / SHIFT_H) if test_rows else 0.0,
        alert_events=alert_events,
    )


@lru_cache(maxsize=1)
def run_study() -> StudyResult:
    """Runs the full, deterministic experimental study on the simulated history.

    Returns:
        The ``StudyResult`` (coefficients, metrics per threshold, baselines,
        a timeline for one machine and the limitations text).
    """
    keys = [key for key, _ in FEATURES]
    train_x: list[list[float]] = []
    train_y: list[int] = []
    train_failures = 0
    tests: list[_MachineTest] = []
    raw_test: list[list[list[float]]] = []
    for machine in MACHINES:
        history = simulate_history(machine)
        hours = _row_hours(history)
        last_row_h = history.hours - HORIZON_H - 1
        train_failures += sum(1 for e in history.failures if e.hour < TEST_START_H)
        test_hours: list[int] = []
        test_rows: list[list[float]] = []
        test_labels: list[int] = []
        for t in hours:
            feature_map = features_at(history, t)
            row = [feature_map[key] for key in keys]
            label = label_at(history, t)
            if t + HORIZON_H < TEST_START_H:
                train_x.append(row)
                train_y.append(label)
            elif t >= TEST_START_H:
                test_hours.append(t)
                test_rows.append(row)
                test_labels.append(label)
        tests.append(_MachineTest(machine, test_hours, test_labels, _test_episodes(history, last_row_h)))
        raw_test.append(test_rows)

    n_train = len(train_x)
    means = [sum(row[j] for row in train_x) / n_train for j in range(len(keys))]
    stds = []
    for j, mean in enumerate(means):
        variance = sum((row[j] - mean) ** 2 for row in train_x) / n_train
        stds.append(math.sqrt(variance) if variance > 1e-12 else 1.0)

    def scale(row: list[float]) -> list[float]:
        return [(v - m) / s for v, m, s in zip(row, means, stds, strict=True)]

    model = fit_logistic([scale(row) for row in train_x], train_y, L2)
    model_scores = [[predict_proba(model, scale(row)) for row in rows] for rows in raw_test]

    flat_labels = [label for test in tests for label in test.labels]
    n_test = len(flat_labels)
    train_rate = sum(train_y) / n_train
    fail_1h_index = keys.index("failures_1h")
    last_hour_scores = [[1.0 if row[fail_1h_index] > 0 else 0.0 for row in rows] for rows in raw_test]
    constant_scores = [[train_rate] * len(rows) for rows in raw_test]

    def flat(scores: list[list[float]]) -> list[float]:
        return [s for machine_scores in scores for s in machine_scores]

    thresholds = [_threshold_row(th, tests, model_scores, n_test) for th in THRESHOLDS]
    baselines = [
        BaselineResult(
            key="last_hour_failure",
            label="Alertar si hubo falla en la última hora",
            pr_auc=average_precision(flat(last_hour_scores), flat_labels),
            at_half=_threshold_row(DEFAULT_THRESHOLD, tests, last_hour_scores, n_test),
        ),
        BaselineResult(
            key="constant_rate",
            label="Tasa constante",
            pr_auc=average_precision(flat(constant_scores), flat_labels),
            at_half=_threshold_row(DEFAULT_THRESHOLD, tests, constant_scores, n_test),
        ),
    ]

    with_total = with_hit = without_total = without_hit = 0
    for test, machine_scores in zip(tests, model_scores, strict=True):
        alerts = [h for h, s in zip(test.hours, machine_scores, strict=True) if s >= DEFAULT_THRESHOLD]
        for event in test.episodes:
            hit = _lead(alerts, event.hour, HORIZON_H) is not None
            if event.has_precursor:
                with_total += 1
                with_hit += int(hit)
            else:
                without_total += 1
                without_hit += int(hit)

    showcase = max(range(len(tests)), key=lambda i: (len(tests[i].episodes), -i))
    history = simulate_history(tests[showcase].machine)
    timeline = StudyTimeline(
        machine=history.machine,
        points=[
            TimelinePoint(
                hour=h,
                score=round(score, 4),
                vibration=history.vibration[h],
                current=history.current[h],
                alarms=history.alarms[h],
            )
            for h, score in zip(tests[showcase].hours, model_scores[showcase], strict=True)
        ],
        failures=[e for e in history.failures if e.hour >= TEST_START_H],
        maintenance_h=[h for h in history.maintenance_h if h >= TEST_START_H],
    )

    features = sorted(
        (
            FeatureWeight(key=key, label=label, coefficient=coef)
            for (key, label), coef in zip(FEATURES, model.coefficients, strict=True)
        ),
        key=lambda weight: -abs(weight.coefficient),
    )
    test_failures = sum(len(test.episodes) for test in tests)
    split = StudySplit(
        description=(
            f"Partición temporal: entrenamiento con las semanas 1–{TRAIN_WEEKS} de las "
            f"{len(MACHINES)} máquinas simuladas (sin filas cuya ventana de {HORIZON_H} h cruce al "
            f"periodo de prueba); prueba con las semanas siguientes, nunca vistas. Estandarización "
            f"con medias y desviaciones del entrenamiento."
        ),
        train_rows=n_train,
        test_rows=n_test,
        train_failures=train_failures,
        test_failures=test_failures,
        test_positive_rate=sum(flat_labels) / n_test if n_test else 0.0,
    )
    return StudyResult(
        engine_name=ENGINE_NAME,
        engine_version=ENGINE_VERSION,
        horizon_h=HORIZON_H,
        split=split,
        features=features,
        intercept=model.intercept,
        model_pr_auc=average_precision(flat(model_scores), flat_labels),
        thresholds=thresholds,
        baselines=baselines,
        timeline=timeline,
        precursor_breakdown=PrecursorBreakdown(
            with_precursor_total=with_total,
            with_precursor_anticipated=with_hit,
            without_precursor_total=without_total,
            without_precursor_anticipated=without_hit,
        ),
        limitations=list(LIMITATIONS),
    )
