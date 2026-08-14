"""
Analytics service.

Sits strictly between persisted telemetry and the API layer:

    EnergyReading (DB) -> AnalyticsService -> metrics/patterns/profile -> API

No calculation lives in the API routes; no analytics endpoint touches the
`TelemetryProvider` directly. This keeps the analytics layer reusable by
future forecasting/decision code without depending on FastAPI request
objects, and keeps API routes limited to request/response marshalling.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, InsufficientDataError, NotFoundError
from app.models.microgrid import Microgrid
from app.models.telemetry import EnergyReading, TelemetrySource
from app.services.analytics.metrics import EnergySummary, compute_energy_summary
from app.services.analytics.patterns import ConsumptionPatterns, analyze_consumption_patterns
from app.services.analytics.profile import CustomerEnergyProfile, build_customer_energy_profile

settings = get_settings()


class InvalidTimeRangeError(AppError):
    status_code = 400
    error_code = "INVALID_RANGE"


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_energy_summary(
        self, microgrid_id: uuid.UUID, start: Optional[datetime], end: Optional[datetime], source: TelemetrySource
    ) -> EnergySummary:
        readings = self._load_readings(microgrid_id, start, end, source)
        return compute_energy_summary(readings)

    def get_consumption_patterns(
        self, microgrid_id: uuid.UUID, start: Optional[datetime], end: Optional[datetime], source: TelemetrySource
    ) -> ConsumptionPatterns:
        readings = self._load_readings(microgrid_id, start, end, source)
        return analyze_consumption_patterns(readings)

    def get_energy_profile(
        self, microgrid_id: uuid.UUID, start: Optional[datetime], end: Optional[datetime], source: TelemetrySource
    ) -> CustomerEnergyProfile:
        readings = self._load_readings(microgrid_id, start, end, source)
        return build_customer_energy_profile(readings)

    # --- internal helpers ---

    def _load_readings(
        self, microgrid_id: uuid.UUID, start: Optional[datetime], end: Optional[datetime], source: TelemetrySource
    ) -> List[EnergyReading]:
        self._require_microgrid(microgrid_id)

        resolved_end = end or datetime.now(timezone.utc)
        resolved_start = start or (resolved_end - timedelta(days=settings.ANALYTICS_DEFAULT_LOOKBACK_DAYS))
        if resolved_start.tzinfo is None:
            resolved_start = resolved_start.replace(tzinfo=timezone.utc)
        if resolved_end.tzinfo is None:
            resolved_end = resolved_end.replace(tzinfo=timezone.utc)

        if resolved_end <= resolved_start:
            raise InvalidTimeRangeError("`end` must be after `start`.")
        if resolved_end - resolved_start > timedelta(days=settings.ANALYTICS_MAX_SPAN_DAYS):
            raise InvalidTimeRangeError(
                f"Requested range exceeds the maximum of {settings.ANALYTICS_MAX_SPAN_DAYS} days."
            )

        # Readings are queried for a single, explicit telemetry source.
        # Mixing SIMULATED and HARDWARE rows in one aggregate would silently
        # blend two different notions of "truth" into one number — a data
        # integrity failure mode analytics must not allow.
        rows = self.db.execute(
            select(EnergyReading)
            .where(EnergyReading.microgrid_id == microgrid_id)
            .where(EnergyReading.source == source)
            .where(EnergyReading.recorded_at >= resolved_start)
            .where(EnergyReading.recorded_at <= resolved_end)
            .order_by(EnergyReading.recorded_at)
        ).scalars().all()

        readings = self._filter_valid(list(rows))

        if len(readings) < settings.ANALYTICS_MIN_READINGS:
            raise InsufficientDataError(
                f"Not enough telemetry to compute analytics for this range: found {len(readings)} "
                f"valid reading(s), need at least {settings.ANALYTICS_MIN_READINGS}. "
                "Fetch more telemetry history (e.g. via /api/telemetry) before requesting analytics.",
                details={
                    "reading_count": len(readings),
                    "required_minimum": settings.ANALYTICS_MIN_READINGS,
                    "start": resolved_start.isoformat(),
                    "end": resolved_end.isoformat(),
                },
            )

        return readings

    @staticmethod
    def _filter_valid(readings: List[EnergyReading]) -> List[EnergyReading]:
        """
        Defensive data-quality filter. The database now enforces
        non-negativity and SOC bounds via CHECK constraints (see the
        telemetry consistency review), so this should be a no-op for any
        row written after that migration — it remains here as a second
        line of defense against any row that predates the constraints or
        arrives from a future ingestion path that bypasses the ORM.
        """
        valid = []
        seen_timestamps = set()
        for r in readings:
            if r.recorded_at in seen_timestamps:
                continue  # duplicate timestamp defensively skipped
            if r.consumption_w is None or r.generation_w is None:
                continue  # missing required values
            if r.consumption_w < 0 or r.generation_w < 0 or r.grid_import_w < 0 or r.grid_export_w < 0:
                continue  # physically invalid
            seen_timestamps.add(r.recorded_at)
            valid.append(r)
        return valid

    def _require_microgrid(self, microgrid_id: uuid.UUID) -> Microgrid:
        microgrid = self.db.get(Microgrid, microgrid_id)
        if microgrid is None:
            raise NotFoundError(f"Microgrid {microgrid_id} not found.")
        return microgrid
