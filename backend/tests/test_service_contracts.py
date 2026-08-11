import uuid
from datetime import datetime, timezone

import pytest

from app.services.ai import AIService, NotImplementedAIService
from app.services.decision_engine import DecisionEngine, NotImplementedDecisionEngine, OperatingMode


def test_ai_service_is_abstract_contract():
    assert AIService.__abstractmethods__ == frozenset(
        {"predict_demand", "predict_solar", "analyze_usage", "generate_recommendation"}
    )


def test_ai_service_placeholder_raises_not_implemented():
    service = NotImplementedAIService()
    now = datetime.now(timezone.utc)
    with pytest.raises(NotImplementedError):
        service.predict_demand(uuid.uuid4(), now, now)
    with pytest.raises(NotImplementedError):
        service.predict_solar(uuid.uuid4(), now, now)
    with pytest.raises(NotImplementedError):
        service.analyze_usage(uuid.uuid4(), now, now)
    with pytest.raises(NotImplementedError):
        service.generate_recommendation(uuid.uuid4(), {})


def test_decision_engine_is_abstract_contract():
    assert DecisionEngine.__abstractmethods__ == frozenset({"evaluate_mode", "plan_load_actions"})


def test_decision_engine_placeholder_raises_not_implemented():
    engine = NotImplementedDecisionEngine()
    with pytest.raises(NotImplementedError):
        engine.evaluate_mode(uuid.uuid4(), {})
    with pytest.raises(NotImplementedError):
        engine.plan_load_actions(uuid.uuid4(), OperatingMode.NORMAL_MODE, {})


def test_operating_modes_defined():
    assert {m.value for m in OperatingMode} == {"NORMAL_MODE", "ECO_MODE", "EMERGENCY_MODE"}
