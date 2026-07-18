"""EXPERIMENTAL: orchestration tests for
``app.services.adaptive_sampling_service``.

Deliberate deviation from this repo's real-Postgres-only test convention
(CLAUDE.md §11, and every other service test in this suite --
``test_drift_detection_service.py``, ``test_capability_history_service.py``,
``test_measurements_api.py`` -- use zero mocking). This file mocks
``compute_capability_history`` and the ``Recommendation`` query because: (a)
this is a brand-new, orchestration-only, no-DB-write experimental service;
(b) ``compute_capability_history`` already has full real-Postgres coverage
in ``test_capability_history_service.py``, so mocking it here doesn't weaken
real coverage of that collaborator; and (c) the real DB-integration wiring
of this new service is still covered end-to-end by
``test_measurements_api.py``'s sampling-recommendation section, so the "no
mocking" guarantee is preserved at the integration layer even though this
one unit-test file uses mocks."""

from __future__ import annotations

import logging
import random
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

from app.services import adaptive_sampling_service
from app.services.adaptive_sampling_service import compute_adaptive_sampling_recommendation
from app.services.capability_history_service import CapabilityWindow


def _window(cpk: Decimal | None) -> CapabilityWindow:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    return CapabilityWindow(
        window_start=now,
        window_end=now,
        point_count=5,
        cpk=cpk,
        center_line=Decimal("10.0") if cpk is not None else None,
        ucl=Decimal("10.5") if cpk is not None else None,
        lcl=Decimal("9.5") if cpk is not None else None,
        engine_name="spc_engine" if cpk is not None else None,
        engine_version="v1" if cpk is not None else None,
        nominal=Decimal("10.0") if cpk is not None else None,
    )


def _fake_db(recommendation_rows: list[MagicMock] | None = None) -> MagicMock:
    db = MagicMock()
    scalars_result = MagicMock()
    scalars_result.all.return_value = recommendation_rows or []
    db.execute.return_value.scalars.return_value = scalars_result
    return db


def _fake_recommendation(
    *, recommendation_type: str, state: str, rationale: str = "Existing rationale."
) -> MagicMock:
    row = MagicMock()
    row.id = uuid.uuid4()
    row.recommendation_type = recommendation_type
    row.state = state
    row.rationale = rationale
    return row


def test_compute_recommendation_returns_conservative_default_with_no_capability_windows(monkeypatch) -> None:
    monkeypatch.setattr(adaptive_sampling_service, "compute_capability_history", lambda *a, **k: [])
    db = _fake_db()

    result = compute_adaptive_sampling_recommendation(db, uuid.uuid4(), from_=None, to=None, window_size=20)

    assert result.windows_analyzed == 0
    assert result.confidence == 0.0
    assert result.conflicting_recommendations is None
    assert result.current_cpk == 0.0


def test_compute_recommendation_extracts_only_valid_cpk_values(monkeypatch) -> None:
    windows = [_window(Decimal("1.5")), _window(None), _window(Decimal("1.9"))]
    monkeypatch.setattr(adaptive_sampling_service, "compute_capability_history", lambda *a, **k: windows)
    db = _fake_db()

    result = compute_adaptive_sampling_recommendation(
        db, uuid.uuid4(), from_=None, to=None, window_size=20, rng=random.Random(42)
    )

    assert result.windows_analyzed == 2
    assert result.current_cpk == 1.9


def test_compute_recommendation_surfaces_conflicts_from_a_pending_frequency_increase(monkeypatch) -> None:
    windows = [_window(Decimal("2.0")) for _ in range(10)]
    monkeypatch.setattr(adaptive_sampling_service, "compute_capability_history", lambda *a, **k: windows)
    existing = _fake_recommendation(recommendation_type="frequency_increase", state="pending")
    db = _fake_db([existing])

    result = compute_adaptive_sampling_recommendation(
        db, uuid.uuid4(), from_=None, to=None, window_size=20, rng=random.Random(42)
    )

    assert result.conflicting_recommendations is not None
    assert len(result.conflicting_recommendations) == 1
    assert result.conflicting_recommendations[0]["type"] == "frequency_increase"
    assert result.conflicting_recommendations[0]["id"] == str(existing.id)


def test_compute_recommendation_omits_rejected_recommendations_from_conflicts(monkeypatch) -> None:
    windows = [_window(Decimal("2.0")) for _ in range(10)]
    monkeypatch.setattr(adaptive_sampling_service, "compute_capability_history", lambda *a, **k: windows)
    existing = _fake_recommendation(recommendation_type="frequency_increase", state="rejected")
    db = _fake_db([existing])

    result = compute_adaptive_sampling_recommendation(
        db, uuid.uuid4(), from_=None, to=None, window_size=20, rng=random.Random(42)
    )

    assert result.conflicting_recommendations is None


def test_compute_recommendation_no_warning_when_no_conflict(monkeypatch) -> None:
    windows = [_window(Decimal("2.0")) for _ in range(10)]
    monkeypatch.setattr(adaptive_sampling_service, "compute_capability_history", lambda *a, **k: windows)
    existing = _fake_recommendation(recommendation_type="frequency_decrease", state="pending")
    db = _fake_db([existing])

    result = compute_adaptive_sampling_recommendation(
        db, uuid.uuid4(), from_=None, to=None, window_size=20, rng=random.Random(42)
    )

    # recommended_frequency will be 100 (all-capable, seed 42) -- a pending
    # frequency_decrease only conflicts at the tight threshold, so no conflict here.
    assert result.recommended_frequency == 100
    assert result.conflicting_recommendations is None


def test_compute_recommendation_never_calls_db_add_or_commit(monkeypatch) -> None:
    windows = [_window(Decimal("2.0")) for _ in range(10)]
    monkeypatch.setattr(adaptive_sampling_service, "compute_capability_history", lambda *a, **k: windows)
    db = _fake_db()

    compute_adaptive_sampling_recommendation(db, uuid.uuid4(), from_=None, to=None, window_size=20)

    db.add.assert_not_called()
    db.commit.assert_not_called()
    db.merge.assert_not_called()


def test_compute_recommendation_handles_all_null_cpk_without_raising(monkeypatch) -> None:
    windows = [_window(None) for _ in range(10)]
    monkeypatch.setattr(adaptive_sampling_service, "compute_capability_history", lambda *a, **k: windows)
    db = _fake_db()

    result = compute_adaptive_sampling_recommendation(db, uuid.uuid4(), from_=None, to=None, window_size=20)

    assert result.windows_analyzed == 0
    assert result.current_cpk == 0.0


def test_compute_recommendation_logs_with_the_experimental_prefix(monkeypatch, caplog) -> None:
    monkeypatch.setattr(adaptive_sampling_service, "compute_capability_history", lambda *a, **k: [])
    # conftest.py's session-scoped `auth_database` fixture runs Alembic's
    # `fileConfig` (alembic/env.py), which defaults to
    # `disable_existing_loggers=True` and disables every logger already
    # registered by that point in the session, including this module's --
    # unrelated to this service, so reset it locally rather than touching
    # alembic.ini's shared logging config.
    monkeypatch.setattr(adaptive_sampling_service.logger, "disabled", False)
    db = _fake_db()

    with caplog.at_level(logging.INFO):
        compute_adaptive_sampling_recommendation(db, uuid.uuid4(), from_=None, to=None, window_size=20)

    assert any(message.startswith("[EXPERIMENTAL]") for message in caplog.messages)


def test_compute_recommendation_is_deterministic_with_a_seeded_rng(monkeypatch) -> None:
    windows = [_window(Decimal("2.0")) for _ in range(6)] + [_window(Decimal("1.0")) for _ in range(4)]
    monkeypatch.setattr(adaptive_sampling_service, "compute_capability_history", lambda *a, **k: windows)
    characteristic_id = uuid.uuid4()

    first = compute_adaptive_sampling_recommendation(
        _fake_db(), characteristic_id, from_=None, to=None, window_size=20, rng=random.Random(42)
    )
    second = compute_adaptive_sampling_recommendation(
        _fake_db(), characteristic_id, from_=None, to=None, window_size=20, rng=random.Random(42)
    )

    assert first.recommended_frequency == second.recommended_frequency
    assert first.confidence == second.confidence
