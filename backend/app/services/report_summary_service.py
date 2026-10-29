"""IQ-F5: historical-report summary shown as a PRECOMPUTED block.

Customer figures never live in the repository (CLAUDE.md §7, plan decision
D1). A deployment may point `DEMO_REPORT_SUMMARY_PATH` at a private JSON
file; otherwise an obviously fictitious placeholder is returned, flagged
`illustrative=True` so the UI labels it as an example.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.quality_analytics import ReportSummary

logger = logging.getLogger(__name__)

MAX_FILE_BYTES = 256 * 1024

PLACEHOLDER = ReportSummary(
    source="placeholder",
    illustrative=True,
    title="Ejemplo ilustrativo de informe histórico",
    period="Período de ejemplo",
    records=1_000_000,
    piece_ids=50_000,
    variables=20,
    nok_definition="Pieza NOK = al menos una cota fuera de tolerancia en la inspección.",
    critical_nest=4,
    critical_nest_relative_risk=10.0,
    relative_risk_basis="Tasa NOK del nido frente a la tasa conjunta del resto de nidos.",
    notes=[
        "Cifras ficticias de ejemplo: configure DEMO_REPORT_SUMMARY_PATH con el resumen privado del cliente.",
        "Las cifras de un estudio histórico no son predicciones de un modelo en línea.",
    ],
)


def load_report_summary() -> ReportSummary:
    path_value = get_settings().demo_report_summary_path
    if not path_value:
        return PLACEHOLDER
    path = Path(path_value)
    try:
        if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("report summary file missing or too large")
        data = json.loads(path.read_text(encoding="utf-8"))
        summary = ReportSummary.model_validate({**data, "source": "private", "illustrative": False})
    except (OSError, ValueError, ValidationError):
        # Never surface the path or file contents; fall back to the placeholder.
        logger.warning("Report summary could not be loaded; using the illustrative placeholder.")
        return PLACEHOLDER
    return summary
