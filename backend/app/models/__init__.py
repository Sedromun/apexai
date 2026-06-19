"""Import all models so their tables register on ``Base.metadata`` (Alembic, create_all)."""

from app.models.base import Base
from app.models.coach_report import CoachReport
from app.models.lap import Lap
from app.models.race_session import RaceSession
from app.models.subscription import Subscription
from app.models.telemetry_trace import TelemetryTrace
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "RaceSession",
    "Lap",
    "TelemetryTrace",
    "CoachReport",
    "Subscription",
]
