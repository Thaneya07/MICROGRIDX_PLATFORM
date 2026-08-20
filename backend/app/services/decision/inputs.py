"""
Optimization inputs.

Gathers everything the optimizer needs for one microgrid: current state
(from the existing, unmodified TelemetryService), a demand and solar
generation forecast (from the existing, unmodified ForecastingService),
and load configuration (from the Load/Customer tables). Nothing here
computes an optimization result — this module only assembles inputs and
reports, explicitly, when a required input is missing.
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.models.customer import Customer
from app.models.forecast import ForecastTarget
from app.models.load import Load
from app.models.microgrid import Microgrid
from app.models.telemetry import TelemetrySource
from app.services.forecasting.service import ForecastingService, InvalidHorizonError
from app.core.errors import InsufficientDataError
from app.services.telemetry.base import TelemetryProvider
from app.services.telemetry.service import TelemetryService

settings = get_settings()


@dataclass(frozen=True)
class ForecastSeries:
    timestamps: List[datetime]
    values_w: List[float]
    model_id: Optional[uuid.UUID]
    model_trained_at: Optional[datetime]


@dataclass
class OptimizationInputs:
    microgrid_id: uuid.UUID
    source: TelemetrySource

    current_consumption_w: float
    current_generation_w: float
    current_battery_soc_percent: Optional[float]
    current_battery_power_w: Optional[float]

    horizon_start: datetime
    horizon_end: datetime
    interval_minutes: int
    n_steps: int

    demand_forecast: Optional[ForecastSeries]
    solar_forecast: Optional[ForecastSeries]
    forecast_unavailable_reason: Optional[str]

    loads: List[Load] = field(default_factory=list)


def gather_optimization_inputs(
    db: Session, provider: TelemetryProvider, microgrid_id: uuid.UUID, source: TelemetrySource
) -> OptimizationInputs:
    microgrid = db.get(Microgrid, microgrid_id)
    if microgrid is None:
        raise NotFoundError(f"Microgrid {microgrid_id} not found.")

    telemetry_service = TelemetryService(db, provider)
    current_reading = telemetry_service.get_current_energy_reading(microgrid_id)

    horizon_start = datetime.now(timezone.utc)
    interval_minutes = settings.DECISION_INTERVAL_MINUTES
    n_steps = settings.DECISION_HORIZON_STEPS
    horizon_end = horizon_start + timedelta(minutes=interval_minutes * n_steps)

    forecasting_service = ForecastingService(db)
    demand_forecast: Optional[ForecastSeries] = None
    solar_forecast: Optional[ForecastSeries] = None
    forecast_unavailable_reason: Optional[str] = None

    try:
        demand_points = forecasting_service.predict(
            microgrid_id, ForecastTarget.DEMAND, source, horizon_start, horizon_end, interval_minutes
        )
        demand_model = forecasting_service.get_latest_model(microgrid_id, ForecastTarget.DEMAND, source)
        demand_forecast = ForecastSeries(
            timestamps=[p.timestamp for p in demand_points],
            values_w=[p.prediction.mean for p in demand_points],
            model_id=demand_model.id if demand_model else None,
            model_trained_at=demand_model.created_at if demand_model else None,
        )

        solar_points = forecasting_service.predict(
            microgrid_id, ForecastTarget.SOLAR_GENERATION, source, horizon_start, horizon_end, interval_minutes
        )
        solar_model = forecasting_service.get_latest_model(microgrid_id, ForecastTarget.SOLAR_GENERATION, source)
        solar_forecast = ForecastSeries(
            timestamps=[p.timestamp for p in solar_points],
            values_w=[p.prediction.mean for p in solar_points],
            model_id=solar_model.id if solar_model else None,
            model_trained_at=solar_model.created_at if solar_model else None,
        )
    except (NotFoundError, InsufficientDataError, InvalidHorizonError) as exc:
        forecast_unavailable_reason = (
            f"Forecast unavailable ({type(exc).__name__}): {exc.message if hasattr(exc, 'message') else str(exc)}"
        )
        demand_forecast = None
        solar_forecast = None

    load_rows = list(
        db.execute(
            select(Load).join(Customer, Load.customer_id == Customer.id).where(Customer.microgrid_id == microgrid_id)
        ).scalars().all()
    )

    return OptimizationInputs(
        microgrid_id=microgrid_id,
        source=current_reading.source,
        current_consumption_w=current_reading.consumption_w,
        current_generation_w=current_reading.generation_w,
        current_battery_soc_percent=current_reading.battery_soc_percent,
        current_battery_power_w=current_reading.battery_power_w,
        horizon_start=horizon_start,
        horizon_end=horizon_end,
        interval_minutes=interval_minutes,
        n_steps=n_steps,
        demand_forecast=demand_forecast,
        solar_forecast=solar_forecast,
        forecast_unavailable_reason=forecast_unavailable_reason,
        loads=load_rows,
    )
