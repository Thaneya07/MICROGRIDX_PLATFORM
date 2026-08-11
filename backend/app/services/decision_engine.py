"""
Decision Engine contract (Phase 1 placeholder).

This module defines the abstract interface for the future Decision Engine,
which will eventually consume AI predictions (demand, solar generation,
usage analysis) and determine the operating mode of a microgrid along with
any load-management actions to take.

IMPORTANT: No decision logic is implemented in Phase 1. There is no
hardcoded mode selection and no simulated load-management action. Every
method is an explicit placeholder that raises NotImplementedError.
"""
import enum
from abc import ABC, abstractmethod
from typing import Any, Dict, List
from uuid import UUID


class OperatingMode(str, enum.Enum):
    """The set of operating modes the Decision Engine will eventually manage."""

    NORMAL_MODE = "NORMAL_MODE"
    ECO_MODE = "ECO_MODE"
    EMERGENCY_MODE = "EMERGENCY_MODE"


class LoadManagementAction:
    """Placeholder type. Structure to be finalized when the Decision Engine is implemented."""


class DecisionEngine(ABC):
    """
    Abstract contract for the future energy-management Decision Engine.

    All methods are intentionally unimplemented in Phase 1. Do not add
    hardcoded mode transitions or fabricated load-management actions —
    that logic belongs to a real Decision Engine implementation in a
    later phase, informed by the AI Service contract.
    """

    @abstractmethod
    def evaluate_mode(self, microgrid_id: UUID, context: Dict[str, Any]) -> OperatingMode:
        """Determine the appropriate operating mode for a microgrid given current context."""
        raise NotImplementedError("DecisionEngine.evaluate_mode is not implemented in Phase 1.")

    @abstractmethod
    def plan_load_actions(
        self,
        microgrid_id: UUID,
        mode: OperatingMode,
        context: Dict[str, Any],
    ) -> List[LoadManagementAction]:
        """Determine load-management actions required to operate in the given mode."""
        raise NotImplementedError("DecisionEngine.plan_load_actions is not implemented in Phase 1.")


class NotImplementedDecisionEngine(DecisionEngine):
    """
    Default DecisionEngine implementation for Phase 1.

    Exists so the application can wire a `DecisionEngine` dependency
    without real decision logic, while guaranteeing that any attempt to
    actually use it fails loudly rather than silently pretending a
    decision was made.
    """

    def evaluate_mode(self, microgrid_id: UUID, context: Dict[str, Any]) -> OperatingMode:
        raise NotImplementedError("Decision Engine mode evaluation is not available in Phase 1.")

    def plan_load_actions(
        self, microgrid_id: UUID, mode: OperatingMode, context: Dict[str, Any]
    ) -> List[LoadManagementAction]:
        raise NotImplementedError("Decision Engine load planning is not available in Phase 1.")
