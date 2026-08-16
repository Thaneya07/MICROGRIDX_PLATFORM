"""
Forecasting service.

Owns the full pipeline:

    EnergyReading (DB, single source)
        -> chronological train/validation/test split
        -> calendar feature preparation
        -> RandomForestRegressor training
        -> evaluation (MAE/RMSE/SMAPE/R2) against a seasonal-naive baseline
        -> persistence (model file + ForecastModel metadata row)

and, separately, prediction using the most recently trained model for a
given (microgrid, target, source).

Never fabricates data or metrics: if there are too few readings to train
or predict, this raises `InsufficientDataError` rather than returning a
result. If no model has been trained yet, `predict()` raises
`NotFoundError` rather than silently training one inline (training is a
deliberate, explicit action — see the API layer).
"""
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, InsufficientDataError, NotFoundError
from app.core.logging import get_logger
from app.models.forecast import ForecastModel, ForecastModelStatus, ForecastTarget
from app.models.microgrid import Microgrid
from app.models.telemetry import EnergyReading, TelemetrySource
from app.services.forecasting.baseline import fit_seasonal_naive_baseline
from app.services.forecasting.features import FEATURE_NAMES, build_feature_matrix
from app.services.forecasting.metrics import compute_regression_metrics
from app.services.forecasting.model import ForecastModelWrapper, PredictionWithUncertainty

settings = get_settings()
logger = get_logger(__name__)

_TARGET_ATTRIBUTE = {
    ForecastTarget.DEMAND: "consumption_w",
    ForecastTarget.SOLAR_GENERATION: "generation_w",
}


class InvalidHorizonError(AppError):
    status_code = 400
    error_code = "INVALID_HORIZON"


class TrainingResult:
    def __init__(self, model_row: ForecastModel):
        self.model_row = model_row


class ForecastPoint:
    def __init__(self, timestamp: datetime, prediction: PredictionWithUncertainty):
        self.timestamp = timestamp
        self.prediction = prediction


class ForecastingService:
    def __init__(self, db: Session):
        self.db = db
        os.makedirs(settings.FORECAST_MODEL_DIR, exist_ok=True)

    # --- training ---

    def train(self, microgrid_id: uuid.UUID, target: ForecastTarget, source: TelemetrySource) -> ForecastModel:
        self._require_microgrid(microgrid_id)

        readings = self._load_training_readings(microgrid_id, source)
        if len(readings) < settings.FORECAST_MIN_TRAINING_READINGS:
            raise InsufficientDataError(
                f"Not enough {source.value} telemetry to train a {target.value} forecasting model: "
                f"found {len(readings)} reading(s), need at least {settings.FORECAST_MIN_TRAINING_READINGS}. "
                "Fetch more telemetry history via /api/telemetry before training.",
                details={
                    "reading_count": len(readings),
                    "required_minimum": settings.FORECAST_MIN_TRAINING_READINGS,
                },
            )

        timestamps = [r.recorded_at for r in readings]
        attribute = _TARGET_ATTRIBUTE[target]
        values = [getattr(r, attribute) for r in readings]

        train_ts, train_y, val_ts, val_y, test_ts, test_y = self._chronological_split(timestamps, values)

        X_train = build_feature_matrix(train_ts)
        X_val = build_feature_matrix(val_ts)
        X_test = build_feature_matrix(test_ts)

        model = ForecastModelWrapper(random_state=settings.FORECAST_RANDOM_STATE)
        model.fit(X_train, train_y)

        val_pred = model.predict(X_val)
        test_pred = model.predict(X_test)
        val_metrics = compute_regression_metrics(val_y, val_pred)
        test_metrics = compute_regression_metrics(test_y, test_pred)

        # Seasonal-naive baseline fit on the same training set, scored on
        # the same test set — the honest floor the model must be compared
        # against. Metrics are reported either way; the caller can see if
        # the trained model actually earned its complexity.
        baseline = fit_seasonal_naive_baseline(train_ts, train_y)
        baseline_test_pred = baseline.predict(test_ts)
        baseline_test_metrics = compute_regression_metrics(test_y, baseline_test_pred)

        model_path = os.path.join(
            settings.FORECAST_MODEL_DIR, f"{microgrid_id}_{target.value}_{source.value}_{uuid.uuid4().hex}.joblib"
        )
        model.save(model_path)

        row = ForecastModel(
            microgrid_id=microgrid_id,
            target=target,
            dataset_source=source,
            status=ForecastModelStatus.TRAINED,
            algorithm=ForecastModelWrapper.ALGORITHM_NAME,
            algorithm_rationale=(
                "RandomForestRegressor selected over deep sequence models (insufficient data volume "
                "at this stage to avoid overfitting) and over boosted trees (bagged ensemble is more "
                "robust to a small dataset with default hyperparameters, and its per-tree spread gives "
                "an honest uncertainty estimate). See app/services/forecasting/model.py for full rationale."
            ),
            feature_set=FEATURE_NAMES,
            training_start=timestamps[0],
            training_end=timestamps[-1],
            n_train=len(train_ts),
            n_validation=len(val_ts),
            n_test=len(test_ts),
            metrics={
                "validation": val_metrics.__dict__,
                "test": test_metrics.__dict__,
                "baseline_test": baseline_test_metrics.__dict__,
            },
            model_path=model_path,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)

        logger.info(
            "Trained forecasting model",
            extra={
                "context": {
                    "microgrid_id": str(microgrid_id),
                    "target": target.value,
                    "source": source.value,
                    "n_train": len(train_ts),
                    "test_mae": test_metrics.mae,
                    "baseline_test_mae": baseline_test_metrics.mae,
                }
            },
        )
        return row

    # --- prediction ---

    def predict(
        self,
        microgrid_id: uuid.UUID,
        target: ForecastTarget,
        source: TelemetrySource,
        start: datetime,
        end: datetime,
        interval_minutes: int,
    ) -> List[ForecastPoint]:
        self._require_microgrid(microgrid_id)

        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        if end <= start:
            raise InvalidHorizonError("`end` must be after `start`.")
        if end - start > timedelta(days=settings.FORECAST_MAX_HORIZON_DAYS):
            raise InvalidHorizonError(
                f"Forecast horizon exceeds the maximum of {settings.FORECAST_MAX_HORIZON_DAYS} days."
            )

        model_row = self._latest_trained_model(microgrid_id, target, source)
        if model_row is None:
            raise NotFoundError(
                f"No trained {target.value} forecasting model exists yet for this microgrid/source. "
                f"POST /api/forecast/microgrids/{microgrid_id}/train first."
            )

        model = ForecastModelWrapper.load(model_row.model_path, random_state=settings.FORECAST_RANDOM_STATE)

        timestamps = self._time_range(start, end, interval_minutes)
        X = build_feature_matrix(timestamps)
        predictions = model.predict_with_uncertainty(X)

        return [ForecastPoint(timestamp=ts, prediction=pred) for ts, pred in zip(timestamps, predictions)]

    def get_latest_model(
        self, microgrid_id: uuid.UUID, target: ForecastTarget, source: TelemetrySource
    ) -> Optional[ForecastModel]:
        self._require_microgrid(microgrid_id)
        return self._latest_trained_model(microgrid_id, target, source)

    def list_models(self, microgrid_id: uuid.UUID, target: Optional[ForecastTarget]) -> List[ForecastModel]:
        self._require_microgrid(microgrid_id)
        query = select(ForecastModel).where(ForecastModel.microgrid_id == microgrid_id)
        if target is not None:
            query = query.where(ForecastModel.target == target)
        query = query.order_by(ForecastModel.created_at.desc())
        return list(self.db.execute(query).scalars().all())

    # --- internal helpers ---

    def _load_training_readings(self, microgrid_id: uuid.UUID, source: TelemetrySource) -> List[EnergyReading]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.FORECAST_MAX_TRAINING_LOOKBACK_DAYS)
        rows = self.db.execute(
            select(EnergyReading)
            .where(EnergyReading.microgrid_id == microgrid_id)
            .where(EnergyReading.source == source)
            .where(EnergyReading.recorded_at >= cutoff)
            .where(EnergyReading.consumption_w >= 0)
            .where(EnergyReading.generation_w >= 0)
            .order_by(EnergyReading.recorded_at)
        ).scalars().all()
        # Defensive de-duplication by timestamp (DB constraint already
        # prevents this going forward; kept here as a second line of
        # defense, consistent with the analytics service).
        seen = set()
        deduped = []
        for r in rows:
            if r.recorded_at in seen:
                continue
            seen.add(r.recorded_at)
            deduped.append(r)
        return deduped

    def _chronological_split(self, timestamps, values):
        n = len(timestamps)
        n_train = max(1, int(n * settings.FORECAST_TRAIN_SPLIT))
        n_val = max(1, int(n * settings.FORECAST_VALIDATION_SPLIT))
        # Ensure at least 1 sample remains for test.
        n_train = min(n_train, n - 2)
        n_val = min(n_val, n - n_train - 1)

        train_ts, train_y = timestamps[:n_train], values[:n_train]
        val_ts, val_y = timestamps[n_train : n_train + n_val], values[n_train : n_train + n_val]
        test_ts, test_y = timestamps[n_train + n_val :], values[n_train + n_val :]
        return train_ts, train_y, val_ts, val_y, test_ts, test_y

    def _latest_trained_model(
        self, microgrid_id: uuid.UUID, target: ForecastTarget, source: TelemetrySource
    ) -> Optional[ForecastModel]:
        return self.db.execute(
            select(ForecastModel)
            .where(ForecastModel.microgrid_id == microgrid_id)
            .where(ForecastModel.target == target)
            .where(ForecastModel.dataset_source == source)
            .where(ForecastModel.status == ForecastModelStatus.TRAINED)
            .order_by(ForecastModel.created_at.desc())
            .limit(1)
        ).scalars().first()

    @staticmethod
    def _time_range(start: datetime, end: datetime, interval_minutes: int) -> List[datetime]:
        step = timedelta(minutes=max(1, interval_minutes))
        points = []
        cursor = start
        while cursor <= end:
            points.append(cursor)
            cursor += step
        return points

    def _require_microgrid(self, microgrid_id: uuid.UUID) -> Microgrid:
        microgrid = self.db.get(Microgrid, microgrid_id)
        if microgrid is None:
            raise NotFoundError(f"Microgrid {microgrid_id} not found.")
        return microgrid
