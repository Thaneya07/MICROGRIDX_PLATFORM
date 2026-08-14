"""
Pydantic schemas for analytics endpoints.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class EnergySummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    start: datetime
    end: datetime
    reading_count: int

    total_consumption_wh: float
    total_generation_wh: float
    solar_self_consumption_wh: float
    grid_import_wh: float
    grid_export_wh: float

    peak_demand_w: float
    average_demand_w: float
    load_factor: Optional[float]

    renewable_contribution_pct: Optional[float]
    grid_dependency_pct: Optional[float]

    battery_charge_wh: Optional[float]
    battery_discharge_wh: Optional[float]
    battery_throughput_wh: Optional[float]


class HourlyPatternResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    hour: int
    average_consumption_w: float
    average_generation_w: float
    sample_count: int


class PeakPeriodResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    hour: int
    average_consumption_w: float


class ConsumptionPatternsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    reading_count: int
    hourly_patterns: List[HourlyPatternResponse]
    weekday_average_consumption_w: Optional[float]
    weekend_average_consumption_w: Optional[float]
    peak_periods: List[PeakPeriodResponse]
    base_load_w: float
    consumption_variability: float
    solar_load_correlation: Optional[float]
    grid_import_wh_share_pct: Optional[float]
    battery_active_fraction: Optional[float]


class UsageCharacteristicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    label: str
    basis: str


class CustomerEnergyProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    start: datetime
    end: datetime
    reading_count: int

    typical_consumption_w: float
    average_demand_w: float
    peak_demand_w: float
    peak_hour: Optional[int]

    solar_utilization_pct: Optional[float]
    grid_dependency_pct: Optional[float]
    load_variability: float

    characteristics: List[UsageCharacteristicResponse]
