from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class MetaResponse(BaseModel):
    edition: Literal["metrology", "industrial"]
    client_label: str | None
    modules: list[str]
