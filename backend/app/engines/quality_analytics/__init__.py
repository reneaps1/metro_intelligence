"""IQ-F5: dimensional quality analytics (pure engines).

`dataset.py` defines a source-agnostic, columnar dimensional dataset;
`synthetic.py` builds the demo dataset; `analytics.py` aggregates any dataset.
"""

from app.engines.quality_analytics.analytics import QualityFilter, overview, variable_detail
from app.engines.quality_analytics.dataset import DimensionalDataset, Variable
from app.engines.quality_analytics.synthetic import SYNTHETIC_DATASET_ID, synthetic_dataset

__all__ = [
    "SYNTHETIC_DATASET_ID",
    "DimensionalDataset",
    "QualityFilter",
    "Variable",
    "overview",
    "synthetic_dataset",
    "variable_detail",
]
