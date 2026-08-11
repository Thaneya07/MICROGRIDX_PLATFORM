"""
AI Service contract (Phase 1 placeholder).

This module defines the abstract interface that future AI services
(demand forecasting, solar generation forecasting, usage analysis, and
recommendation generation) must implement.

IMPORTANT: No AI logic is implemented in Phase 1. Every method is an
explicit placeholder that raises NotImplementedError. Concrete
implementations (statistical models, ML models, external inference
services, etc.) are out of scope for this phase and must be added in a
future phase behind this same contract.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List
from uuid import UUID


class DemandForecast:
    """Placeholder type. Structure to be finalized when AI is implemented."""


class SolarForecast:
    """Placeholder type. Structure to be finalized when AI is implemented."""


class UsageAnalysis:
    """Placeholder type. Structure to be finalized when AI is implemented."""


class Recommendation:
    """Placeholder type. Structure to be finalized when AI is implemented."""


class AIService(ABC):
    """
    Abstract contract for AI-driven prediction and analysis capabilities.

    All methods are intentionally unimplemented in Phase 1. Do not add
    fabricated predictions, accuracy figures, or recommendations here —
    that logic belongs to a real AI implementation in a later phase.
    """

    @abstractmethod
    def predict_demand(
        self,
        customer_id: UUID,
        horizon_start: datetime,
        horizon_end: datetime,
    ) -> List[DemandForecast]:
        """Forecast future energy demand for a customer over a time horizon."""
        raise NotImplementedError("AIService.predict_demand is not implemented in Phase 1.")

    @abstractmethod
    def predict_solar(
        self,
        microgrid_id: UUID,
        horizon_start: datetime,
        horizon_end: datetime,
    ) -> List[SolarForecast]:
        """Forecast future solar/renewable generation for a microgrid."""
        raise NotImplementedError("AIService.predict_solar is not implemented in Phase 1.")

    @abstractmethod
    def analyze_usage(
        self,
        customer_id: UUID,
        window_start: datetime,
        window_end: datetime,
    ) -> UsageAnalysis:
        """Analyze historical usage patterns for a customer over a time window."""
        raise NotImplementedError("AIService.analyze_usage is not implemented in Phase 1.")

    @abstractmethod
    def generate_recommendation(
        self,
        customer_id: UUID,
        context: Dict[str, Any],
    ) -> List[Recommendation]:
        """Generate personalized energy-saving recommendations for a customer."""
        raise NotImplementedError("AIService.generate_recommendation is not implemented in Phase 1.")


class NotImplementedAIService(AIService):
    """
    Default AIService implementation for Phase 1.

    Exists so the application can wire an `AIService` dependency without
    a concrete AI backend, while guaranteeing that any attempt to actually
    use AI functionality fails loudly rather than returning fabricated
    data.
    """

    def predict_demand(self, customer_id: UUID, horizon_start: datetime, horizon_end: datetime) -> List[DemandForecast]:
        raise NotImplementedError("Demand forecasting is not available in Phase 1.")

    def predict_solar(self, microgrid_id: UUID, horizon_start: datetime, horizon_end: datetime) -> List[SolarForecast]:
        raise NotImplementedError("Solar forecasting is not available in Phase 1.")

    def analyze_usage(self, customer_id: UUID, window_start: datetime, window_end: datetime) -> UsageAnalysis:
        raise NotImplementedError("Usage analysis is not available in Phase 1.")

    def generate_recommendation(self, customer_id: UUID, context: Dict[str, Any]) -> List[Recommendation]:
        raise NotImplementedError("Recommendation generation is not available in Phase 1.")
