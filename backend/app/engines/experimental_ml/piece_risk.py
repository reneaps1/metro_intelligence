"""IQ-F12: per-piece NOK risk *before* the piece is inspected (experimental).

Question: knowing only what happened to earlier pieces, which pieces deserve
an extra check? The features look strictly at the past of each piece:

- recent NOK rate of its group (e.g. mold cavity) over the last 20 and 100 pieces,
- cumulative NOK rate of that group (smoothed),
- recent NOK rate of the whole line (last 200 pieces),
- recent NOK rate of its second group (e.g. nest) over the last 50 pieces.

A logistic regression (pure Python, Newton/IRLS from ``failure_prediction``)
is trained on the earlier days and tested on the last day, and compared on
the same test pieces with two transparent baselines: the recent cavity rate
alone, and the cavity alarm rule. Negatives of the training set are thinned
deterministically to keep training fast; this shifts the intercept only, so
rankings (ROC-AUC, PR-AUC, top-k) are unaffected.

Pure and shadow-mode only (CLAUDE.md §22).
"""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.engines.experimental_ml.failure_prediction import average_precision, fit_logistic, predict_proba

ENGINE_NAME = "piece_risk_engine"
ENGINE_VERSION = "v1-experimental"  # never drop "-experimental": shadow-mode only.

FEATURES = (
    ("group_rate_20", "Tasa NOK reciente de la cavidad (20 piezas)"),
    ("group_rate_100", "Tasa NOK reciente de la cavidad (100 piezas)"),
    ("group_rate_cum", "Tasa NOK acumulada de la cavidad"),
    ("line_rate_200", "Tasa NOK reciente de la línea (200 piezas)"),
    ("second_rate_50", "Tasa NOK reciente del nido (50 piezas)"),
)
TOP_SHARES = (0.01, 0.02, 0.05, 0.10, 0.20)
MAX_TRAIN_NEGATIVES = 25_000
L2 = 1.0


@dataclass(frozen=True)
class TopK:
    share: float
    flagged: int
    nok_caught: int
    precision: float
    recall: float
    lift: float


@dataclass(frozen=True)
class ScoreEval:
    key: str
    name: str
    roc_auc: float
    pr_auc: float
    top: list[TopK]


@dataclass(frozen=True)
class RiskStudy:
    train_pieces: int
    train_nok: int
    test_pieces: int
    test_nok: int
    test_day: str
    excluded_pieces: int
    model: ScoreEval
    baselines: list[ScoreEval]
    # Standardized coefficients (same order as FEATURES).
    coefficients: list[tuple[str, str, float]]
    # Test day, per plant-local hour: mean predicted risk vs. actual NOK rate.
    hours: list[tuple[float, int, float, float]] = field(default_factory=list)
    # Operating point of the cavity alarm rule on the test day.
    alarm_rule: TopK | None = None


def roc_auc(scores: Sequence[float], labels: Sequence[int]) -> float:
    """Rank-based ROC-AUC (Mann-Whitney U), ties get the average rank. 0.5 without both classes."""
    pos = sum(labels)
    neg = len(labels) - pos
    if pos == 0 or neg == 0:
        return 0.5
    order = sorted(range(len(scores)), key=lambda i: scores[i])
    rank_sum = 0.0
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        avg_rank = (i + j) / 2 + 1
        rank_sum += avg_rank * sum(labels[order[t]] for t in range(i, j + 1))
        i = j + 1
    return (rank_sum - pos * (pos + 1) / 2) / (pos * neg)


def top_k(scores: Sequence[float], labels: Sequence[int]) -> list[TopK]:
    """Precision/recall when the highest-scored share of pieces is sent to review."""
    n = len(scores)
    total = sum(labels)
    base = total / n if n else 0.0
    order = sorted(range(n), key=lambda i: (-scores[i], i))
    out = []
    for share in TOP_SHARES:
        flagged = max(1, int(n * share))
        caught = sum(labels[i] for i in order[:flagged])
        precision = caught / flagged
        out.append(
            TopK(
                share=share,
                flagged=flagged,
                nok_caught=caught,
                precision=precision,
                recall=caught / total if total else 0.0,
                lift=precision / base if base else 0.0,
            )
        )
    return out


def _evaluate(key: str, name: str, scores: Sequence[float], labels: Sequence[int]) -> ScoreEval:
    return ScoreEval(
        key, name, roc_auc(scores, labels), average_precision(scores, labels), top_k(scores, labels)
    )


def past_features(
    groups: Sequence[int | None], seconds: Sequence[int | None], nok: Sequence[bool]
) -> list[list[float] | None]:
    """Feature rows from the past of each piece only (None when a group is missing)."""
    g20: dict[int, deque[bool]] = {}
    g100: dict[int, deque[bool]] = {}
    gcum: dict[int, list[int]] = {}
    s50: dict[int, deque[bool]] = {}
    line: deque[bool] = deque(maxlen=200)
    rows: list[list[float] | None] = []

    def rate(d: deque[bool] | None) -> float:
        return sum(d) / len(d) if d else 0.0

    for g, s, bad in zip(groups, seconds, nok, strict=True):
        if g is None or s is None:
            rows.append(None)
        else:
            cum = gcum.get(g, [0, 0])
            rows.append(
                [
                    rate(g20.get(g)),
                    rate(g100.get(g)),
                    (cum[1] + 1) / (cum[0] + 2),  # Laplace-smoothed cumulative rate
                    rate(line),
                    rate(s50.get(s)),
                ]
            )
        # Update the history *after* building the row: the piece never sees itself.
        line.append(bad)
        if g is not None:
            g20.setdefault(g, deque(maxlen=20)).append(bad)
            g100.setdefault(g, deque(maxlen=100)).append(bad)
            c = gcum.setdefault(g, [0, 0])
            c[0] += 1
            c[1] += bad
        if s is not None:
            s50.setdefault(s, deque(maxlen=50)).append(bad)
    return rows


def alarm_rule_flags(groups: Sequence[int | None], nok: Sequence[bool], k: int, n: int) -> list[bool]:
    """Whether each piece's group was already in alarm (>= k NOK in its last n pieces) before it."""
    windows: dict[int, deque[bool]] = {}
    flags = []
    for g, bad in zip(groups, nok, strict=True):
        w = windows.setdefault(g, deque(maxlen=n)) if g is not None else None
        flags.append(bool(w is not None and sum(w) >= k))
        if w is not None:
            w.append(bad)
    return flags


def run_risk_study(
    timestamps: Sequence[float],
    groups: Sequence[int | None],
    seconds: Sequence[int | None],
    nok: Sequence[bool],
    utc_offset_s: int = 0,
    alarm_k: int = 6,
    alarm_n: int = 30,
) -> RiskStudy:
    """Train on every plant-local day but the last; test on the last one."""
    rows = past_features(groups, seconds, nok)
    flags = alarm_rule_flags(groups, nok, alarm_k, alarm_n)
    days = [datetime.fromtimestamp(t + utc_offset_s, tz=UTC).strftime("%Y-%m-%d") for t in timestamps]
    test_day = max(days) if days else ""
    train_x: list[list[float]] = []
    train_y: list[int] = []
    test_x: list[list[float]] = []
    test_y: list[int] = []
    test_idx: list[int] = []
    excluded = 0
    for i, (row, bad) in enumerate(zip(rows, nok, strict=True)):
        if row is None:
            excluded += 1
            continue
        if days[i] == test_day:
            test_x.append(row)
            test_y.append(int(bad))
            test_idx.append(i)
        else:
            train_x.append(row)
            train_y.append(int(bad))
    if not train_x or not test_x or sum(train_y) == 0:
        raise ValueError("not enough data for a temporal split")

    # Standardize with training statistics.
    p = len(FEATURES)
    means = [sum(r[j] for r in train_x) / len(train_x) for j in range(p)]
    sds = [math.sqrt(sum((r[j] - means[j]) ** 2 for r in train_x) / len(train_x)) or 1.0 for j in range(p)]

    def z(r: list[float]) -> list[float]:
        return [(r[j] - means[j]) / sds[j] for j in range(p)]

    # Keep every positive and a deterministic, evenly spaced subset of negatives.
    negatives = [i for i, y in enumerate(train_y) if not y]
    step = max(1, math.ceil(len(negatives) / MAX_TRAIN_NEGATIVES))
    keep = sorted({i for i, y in enumerate(train_y) if y} | set(negatives[::step]))
    model = fit_logistic([z(train_x[i]) for i in keep], [train_y[i] for i in keep], L2)
    scores = [predict_proba(model, z(r)) for r in test_x]

    hours: dict[float, list[float]] = {}
    for i, s, y in zip(test_idx, scores, test_y, strict=True):
        local = timestamps[i] + utc_offset_s
        start = local - local % 3600 - utc_offset_s
        h = hours.setdefault(start, [0, 0.0, 0])
        h[0] += 1
        h[1] += s
        h[2] += y
    test_flags = [flags[i] for i in test_idx]
    flagged = sum(test_flags)
    caught = sum(1 for f, y in zip(test_flags, test_y, strict=True) if f and y)
    base = sum(test_y) / len(test_y)
    rule_point = TopK(
        share=flagged / len(test_y),
        flagged=flagged,
        nok_caught=caught,
        precision=caught / flagged if flagged else 0.0,
        recall=caught / sum(test_y) if sum(test_y) else 0.0,
        lift=(caught / flagged) / base if flagged and base else 0.0,
    )
    return RiskStudy(
        train_pieces=len(train_x),
        train_nok=sum(train_y),
        test_pieces=len(test_x),
        test_nok=sum(test_y),
        test_day=test_day,
        excluded_pieces=excluded,
        model=_evaluate("logistic", "Regresión logística (5 variables del pasado)", scores, test_y),
        baselines=[
            _evaluate(
                "cavity_rate", "Línea base: tasa reciente de la cavidad", [r[1] for r in test_x], test_y
            ),
            _evaluate(
                "alarm_rule",
                f"Línea base: alarma ≥{alarm_k} NOK en {alarm_n} piezas",
                [float(f) for f in test_flags],
                test_y,
            ),
        ],
        coefficients=[(key, name, c) for (key, name), c in zip(FEATURES, model.coefficients, strict=True)],
        hours=[(ts, int(v[0]), v[1] / v[0], v[2] / v[0]) for ts, v in sorted(hours.items())],
        alarm_rule=rule_point,
    )
