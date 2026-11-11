"""IQ-F26: fictitious twin parts for the public part selector (D23)."""

from __future__ import annotations

import pytest
from app.engines.quality_analytics.analytics import QualityFilter, overview
from app.engines.quality_analytics.twins import TWIN_NOTE, TWINS, build_twin, twin_ids, twin_meta
from app.services import dataset_registry


@pytest.mark.parametrize("slug", sorted(TWINS))
def test_twins_are_simulated_deterministic_and_plausible(slug: str) -> None:
    ds = build_twin(slug)
    assert ds.source_type == "SIMULATED" and TWIN_NOTE in ds.description
    assert ds.name.startswith("MI-DEMO-") and ds.nok_basis == "reported"
    assert all(b >= a for a, b in zip(ds.timestamps, ds.timestamps[1:], strict=False))
    rate = sum(1 for x in ds.reported_nok or [] if x) / len(ds)
    assert 0.003 < rate < 0.05
    build_twin.cache_clear()
    again = build_twin(slug)
    assert again.values == ds.values and again.reported_nok == ds.reported_nok
    # A failed piece is not tested by later stations.
    keys = [s.key for s in ds.stations]
    for i in range(len(ds)):
        seen_fail = False
        for k in keys:
            v = ds.station_nok[k][i]
            if seen_fail:
                assert v is None
            seen_fail = seen_fail or bool(v)


def test_twins_resolve_with_their_vocabulary() -> None:
    for dataset_id in twin_ids():
        ds = dataset_registry.resolve(dataset_id)
        assert ds.id == dataset_id
        result = overview(ds, QualityFilter(), "day")
        assert result
    line, labels, _ = twin_meta("demo-linea-a-tipo-1")  # type: ignore[misc]
    assert labels == {"primary": "Nido", "secondary": "Lado"} and "Línea demo A" in line
    _, labels_b, _ = twin_meta("demo-linea-b-familia-9")  # type: ignore[misc]
    assert labels_b == {"primary": "Cavidad"}
    assert dataset_registry.resolve("demo-linea-b-familia-9").mold_cavities is None
    assert twin_meta("demo-synthetic-dimensional") is None
