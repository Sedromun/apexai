from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class CoachAnalyzeRequest(BaseModel):
    lap_id: uuid.UUID


class CoachReportOut(BaseModel):
    # protected_namespaces=() allows the field literally named "model".
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: uuid.UUID
    lap_id: uuid.UUID
    summary: dict[str, Any]
    body: str
    model: str
    created_at: datetime
