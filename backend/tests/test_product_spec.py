"""IQ-F28: private product specification (drawing names and limits) applied per part.

Fictitious data only: parts are converted in ``tmp_path`` from the synthetic export.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from app.connectors.long_signal_batch import convert
from app.connectors.product_spec import (
    ProductSpec,
    apply_product_spec,
    product_label,
    read_product_spec,
)
from app.core.config import get_settings
from app.engines.quality_analytics.analytics import QualityFilter, overview, variable_detail
from app.services import dataset_registry
from pydantic import ValidationError

from test_long_signal_batch import _mapping, export  # noqa: F401  (fixture re-export)

SPEC = {
    "format": "product-spec-v1",
    "product": {
        "name": "Conector demo",
        "part_number": "MI-DEMO-0042",
        "drawing": "MI-DEMO-DWG-7 rev B",
        "customer_program": "Programa demo",
    },
    "characteristics": [
        {"variable": "x0", "name": "Altura pin 1", "balloon": "12", "nominal": 1.2, "lsl": 0.9, "usl": 1.5},
        {"variable": "x1", "usl": 3.0, "class": "CC"},
    ],
}


@pytest.fixture
def part(export: list[Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:  # noqa: F811
    root = tmp_path / "private"
    convert(export, _mapping(), root / "pieza-demo", partitions=1)
    settings = get_settings()
    for key, value in {
        "app_edition": "industrial",
        "app_env": "development",
        "cors_origins": "http://localhost:5173",
        "demo_real_datasets_dir": str(root),
        "demo_private_host_authorization": None,
    }.items():
        monkeypatch.setattr(settings, key, value)
    for marker in ("RENDER", "RENDER_SERVICE_ID"):
        monkeypatch.delenv(marker, raising=False)
    dataset_registry.reset_cache()
    yield root / "pieza-demo"
    dataset_registry.reset_cache()


def test_reader_validates_limits_and_duplicates(tmp_path: Path) -> None:
    good = tmp_path / "product.json"
    good.write_text(json.dumps(SPEC), encoding="utf-8")
    assert read_product_spec(good).product.part_number == "MI-DEMO-0042"
    for bad in (
        {**SPEC, "characteristics": [{"variable": "x0", "lsl": 2.0, "usl": 1.0}]},
        {**SPEC, "characteristics": [{"variable": "x0", "nominal": 5.0, "lsl": 0.0, "usl": 1.0}]},
        {**SPEC, "characteristics": [{"variable": "x0"}, {"variable": "x0"}]},
        {**SPEC, "format": "other"},
    ):
        with pytest.raises(ValidationError):
            ProductSpec.model_validate(bad)


def test_label_composition() -> None:
    spec = ProductSpec.model_validate(SPEC)
    assert product_label(spec, "fallback") == "Programa demo · Conector demo (MI-DEMO-0042)"
    assert product_label(None, "fallback") == "fallback"
    assert product_label(ProductSpec.model_validate({"format": "product-spec-v1"}), "fb") == "fb"


def test_registry_applies_drawing_limits_without_touching_verdicts(part: Path) -> None:
    before = dataset_registry.resolve("real-pieza-demo")
    nok_before = overview(before, QualityFilter(), "day")["summary"]["nok_pieces"]
    assert all(v.lsl is None and v.usl is None for v in before.variables)

    (part / "product.json").write_text(json.dumps(SPEC), encoding="utf-8")
    entry = dataset_registry.entry("real-pieza-demo")
    assert entry is not None and entry.label == "Programa demo · Conector demo (MI-DEMO-0042)"
    after = dataset_registry.resolve("real-pieza-demo")
    assert after is not before  # the product file is part of the cache signature
    x0 = next(v for v in after.variables if v.key == "x0")
    assert (x0.name, x0.lsl, x0.usl, x0.display_nominal) == ("Altura pin 1 (globo 12)", 0.9, 1.5, 1.2)
    x1 = next(v for v in after.variables if v.key == "x1")
    assert x1.lsl is None and x1.usl == 3.0
    # The machine verdict stays the NOK basis.
    assert overview(after, QualityFilter(), "day")["summary"]["nok_pieces"] == nok_before
    detail = variable_detail(after, QualityFilter(), "x0", "cavity")
    assert detail["spec"]["lsl"] == 0.9 and detail["spec"]["usl"] == 1.5


def test_a_spec_for_another_part_is_not_applied(part: Path) -> None:
    other = {**SPEC, "characteristics": [{"variable": "not_here", "usl": 1.0}]}
    (part / "product.json").write_text(json.dumps(other), encoding="utf-8")
    ds = dataset_registry.resolve("real-pieza-demo")
    assert all(v.usl is None for v in ds.variables)  # offered, but without foreign limits
    with pytest.raises(ValueError):
        apply_product_spec(ds, ProductSpec.model_validate(other))


def test_invalid_product_file_keeps_the_part_offered(part: Path) -> None:
    (part / "product.json").write_text("{broken", encoding="utf-8")
    entry = dataset_registry.entry("real-pieza-demo")
    assert entry is not None and entry.product is None
    assert dataset_registry.resolve("real-pieza-demo").id == "real-pieza-demo"


def test_drawing_concordance_and_pareto_by_hand(part: Path) -> None:
    """Hand-checkable vector: every piece is classified by machine verdict vs. drawing limits."""
    ds = dataset_registry.resolve("real-pieza-demo")
    tight = {
        "format": "product-spec-v1",
        "characteristics": [{"variable": "x0", "lsl": 1.05, "usl": 1.45}],
    }
    limited = apply_product_spec(ds, ProductSpec.model_validate(tight))
    result = overview(limited, QualityFilter(), "day")
    concordance = result["drawing_concordance"]
    expected = {k: 0 for k in concordance}
    verdicts = limited.reported_nok or []
    for i, x in enumerate(limited.values["x0"]):
        if verdicts[i] is None:
            continue
        if x is None:
            expected["not_measured"] += 1
            continue
        out = not 1.05 <= x <= 1.45
        expected[f"machine_{'nok' if verdicts[i] else 'ok'}_drawing_{'out' if out else 'ok'}"] += 1
    assert concordance == expected
    assert sum(concordance.values()) == result["summary"]["pieces"]
    rows = result["drawing_pareto"]
    assert [r["variable"] for r in rows] == ["x0"]
    assert rows[0]["nok"] == concordance["machine_ok_drawing_out"] + concordance["machine_nok_drawing_out"]
    assert result["pareto"] == []  # the official Pareto of a machine-verdict dataset stays empty
    plain = overview(ds, QualityFilter(), "day")
    assert plain["drawing_concordance"] is None and plain["drawing_pareto"] == []
