"""IQ-F7: precomputed model lab -- derived metrics and private-file handling."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from app.core.config import get_settings
from app.services.model_lab_service import PLACEHOLDER, load_model_lab

STUDY = {
    "title": "Estudio de prueba",
    "study_date": "2026",
    "dataset_description": "Ficticio",
    "split_description": "Temporal",
    "variables": 5,
    "models": [
        {
            "key": "gb",
            "name": "GB",
            "family": "ml_tabular",
            "roc_auc": 0.9,
            "pr_auc": 0.06,
            "recall": 0.8,
            "precision": 0.04,
            "confusion": {"tp": 8, "fp": 192, "fn": 2, "tn": 798},
        },
        {
            "key": "mlp",
            "name": "MLP",
            "family": "deep_learning",
            "roc_auc": 0.88,
            "pr_auc": 0.05,
            "recall": 0.9,
            "precision": 0.03,
            "confusion": {"tp": 9, "fp": 291, "fn": 1, "tn": 699},
        },
    ],
}


@pytest.fixture
def lab_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[[object], None]]:
    path = tmp_path / "model-lab.json"
    monkeypatch.setattr(get_settings(), "demo_model_lab_path", str(path))

    def _write(content: object) -> None:
        path.write_text(json.dumps(content) if not isinstance(content, str) else content, encoding="utf-8")

    yield _write


def test_placeholder_is_illustrative_and_consistent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "demo_model_lab_path", None)
    lab = load_model_lab()
    assert lab.source == "placeholder" and lab.illustrative
    assert all(m.consistent for m in lab.models)
    gb = next(m for m in lab.models if m.key == "gb")
    assert gb.fp_per_tp == pytest.approx(2400 / 50)
    assert gb.alarm_rate == pytest.approx(2450 / 10_000)
    assert lab.test_n == 10_000 and lab.test_positives == 60
    assert lab.dl_beats_ml is False
    assert lab.has_threshold_results is False
    assert len(lab.models) == len(PLACEHOLDER.models)


def test_private_file_derives_metrics_by_hand(lab_file) -> None:
    lab_file(STUDY)
    lab = load_model_lab()
    assert lab.source == "private" and not lab.illustrative
    gb, mlp = lab.models
    # GB: 8 of 10 NOK caught with 192 false alarms -> 24 per NOK caught; 200 of 1000 flagged.
    assert (gb.fp_per_tp, gb.alarm_rate, gb.consistent) == (24.0, 0.2, True)
    assert mlp.fp_per_tp == pytest.approx(291 / 9)
    assert lab.prevalence == pytest.approx(0.01)
    assert (lab.best_ml, lab.best_dl, lab.dl_beats_ml) == ("gb", "mlp", False)


def test_reported_metrics_that_contradict_the_matrix_are_flagged(lab_file) -> None:
    study = json.loads(json.dumps(STUDY))
    study["models"][0]["recall"] = 0.95
    lab_file(study)
    assert load_model_lab().models[0].consistent is False


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        {"title": "sin modelos"},
        # models evaluated on different test sets cannot be compared
        {
            **STUDY,
            "models": [
                STUDY["models"][0],
                {**STUDY["models"][1], "confusion": {"tp": 9, "fp": 1, "fn": 1, "tn": 1}},
            ],
        },
    ],
)
def test_bad_private_files_fall_back_to_the_placeholder(lab_file, content: object) -> None:
    lab_file(content)
    assert load_model_lab().source == "placeholder"
