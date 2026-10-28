"""IQ-F7: precomputed ML/DL study results for the predictive lab.

Same rule as the F5 report summary (plan decision D1): customer figures never
live in the repository. A deployment may point `DEMO_MODEL_LAB_PATH` at a
private JSON file; otherwise an obviously fictitious placeholder is served,
flagged `illustrative=True`.

Nothing here is a live model: these are the results of a closed historical
study, shown as PRECOMPUTED. The service only derives what follows
arithmetically from each confusion matrix (false alarms per detected NOK,
alarm rate) and checks it against the reported recall/precision, so a typo in
the file shows up as `consistent=False` instead of a silently wrong chart.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.predictive import Confusion, ModelLab, ModelLabIn, ModelMetrics, ModelResultIn

logger = logging.getLogger(__name__)

MAX_FILE_BYTES = 256 * 1024
CONSISTENCY_TOLERANCE = 0.005

PLACEHOLDER = ModelLabIn(
    title="Ejemplo ilustrativo de estudio ML/DL",
    study_date="Fecha de ejemplo",
    dataset_description="Cifras ficticias: 10 000 piezas de prueba, 60 NOK (0.6 %).",
    split_description=(
        "Partición temporal de ejemplo: entrenamiento con el período inicial, prueba con el final."
    ),
    variables=20,
    models=[
        ModelResultIn(
            key="gb",
            name="Gradient Boosting",
            family="ml_tabular",
            roc_auc=0.85,
            pr_auc=0.05,
            recall=50 / 60,
            precision=50 / 2450,
            confusion=Confusion(tp=50, fp=2400, fn=10, tn=7540),
        ),
        ModelResultIn(
            key="mlp_balanced",
            name="MLP con balanceo de clases",
            family="deep_learning",
            roc_auc=0.84,
            pr_auc=0.045,
            recall=51 / 60,
            precision=51 / 3151,
            confusion=Confusion(tp=51, fp=3100, fn=9, tn=6840),
        ),
        ModelResultIn(
            key="mlp_weighted",
            name="MLP con peso NOK alto",
            family="deep_learning",
            roc_auc=0.83,
            pr_auc=0.04,
            recall=10 / 60,
            precision=10 / 200,
            confusion=Confusion(tp=10, fp=190, fn=50, tn=9750),
        ),
    ],
    notes=[
        "Cifras ficticias de ejemplo: configure DEMO_MODEL_LAB_PATH con los resultados privados del estudio.",
        "Resultados de un estudio histórico cerrado, no de un modelo en línea.",
    ],
)


def _metrics(m: ModelResultIn) -> ModelMetrics:
    c = m.confusion
    test_n = c.tp + c.fp + c.fn + c.tn
    positives = c.tp + c.fn
    flagged = c.tp + c.fp
    recall = c.tp / positives if positives else 0.0
    precision = c.tp / flagged if flagged else 0.0
    consistent = (
        abs(recall - m.recall) <= CONSISTENCY_TOLERANCE
        and abs(precision - m.precision) <= CONSISTENCY_TOLERANCE
    )
    return ModelMetrics(
        **m.model_dump(),
        test_n=test_n,
        positives=positives,
        flagged=flagged,
        fp_per_tp=c.fp / c.tp if c.tp else None,
        alarm_rate=flagged / test_n if test_n else 0.0,
        consistent=consistent,
    )


def _best(models: list[ModelMetrics], family: str) -> ModelMetrics | None:
    candidates = [m for m in models if m.family == family]
    return max(candidates, key=lambda m: (m.pr_auc, m.roc_auc)) if candidates else None


def build_model_lab(study: ModelLabIn, *, source: str) -> ModelLab:
    models = [_metrics(m) for m in study.models]
    reference = models[0]
    best_ml, best_dl = _best(models, "ml_tabular"), _best(models, "deep_learning")
    return ModelLab(
        source="private" if source == "private" else "placeholder",
        illustrative=source != "private",
        title=study.title,
        study_date=study.study_date,
        dataset_description=study.dataset_description,
        split_description=study.split_description,
        variables=study.variables,
        test_n=reference.test_n,
        test_positives=reference.positives,
        prevalence=reference.positives / reference.test_n if reference.test_n else 0.0,
        models=models,
        best_ml=best_ml.key if best_ml else None,
        best_dl=best_dl.key if best_dl else None,
        dl_beats_ml=None if best_ml is None or best_dl is None else best_dl.pr_auc > best_ml.pr_auc,
        has_threshold_results=False,
        notes=study.notes,
    )


def _validated(study: ModelLabIn) -> ModelLabIn:
    sizes = {(m.confusion.tp + m.confusion.fn, sum(m.confusion.model_dump().values())) for m in study.models}
    if len(sizes) != 1:
        raise ValueError("models were not evaluated on the same test set")
    return study


MAX_STUDIES = 4


def _studies(data: object) -> list[ModelLabIn]:
    """One study, or IQ-F12 ``{"studies": [...]}`` (up to 4, each on its own test set)."""
    if isinstance(data, dict) and "studies" in data:
        items = data["studies"]
        if not isinstance(items, list) or not 1 <= len(items) <= MAX_STUDIES:
            raise ValueError("studies must hold 1 to 4 studies")
        return [_validated(ModelLabIn.model_validate(item)) for item in items]
    return [_validated(ModelLabIn.model_validate(data))]


def load_model_lab() -> ModelLab:
    path_value = get_settings().demo_model_lab_path
    if not path_value:
        return build_model_lab(PLACEHOLDER, source="placeholder")
    path = Path(path_value)
    try:
        if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("model lab file missing or too large")
        studies = _studies(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, ValidationError):
        # Never surface the path or file contents; fall back to the placeholder.
        logger.warning("Model lab results could not be loaded; using the illustrative placeholder.")
        return build_model_lab(PLACEHOLDER, source="placeholder")
    primary, *others = (build_model_lab(study, source="private") for study in studies)
    return primary.model_copy(update={"additional_studies": others})
