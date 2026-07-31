from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from app.core.config import settings
from app.core.response import BizException
from app.models import Customer, Experiment
from app.utils.data_processor import (
    FEATURE_COLUMNS,
    customers_dataframe,
    prepare_features,
)


class MLService:
    def _get_model(self, name: str, y_train, params: dict[str, Any]):
        if name == "logistic_regression":
            return LogisticRegression(class_weight="balanced", max_iter=1000, **params)
        if name == "random_forest":
            return RandomForestClassifier(
                class_weight="balanced", n_estimators=120, n_jobs=-1, random_state=42, **params
            )
        if name == "xgboost":
            positives = int((y_train == 1).sum())
            negatives = int((y_train == 0).sum())
            defaults = {
                "scale_pos_weight": negatives / positives if positives else 1,
                "n_estimators": 150,
                "max_depth": 6,
                "learning_rate": 0.1,
                "n_jobs": -1,
                "random_state": 42,
                "eval_metric": "logloss",
            }
            return XGBClassifier(**(defaults | params))
        raise BizException(1001, "不支持的模型", 400)

    def train(
        self,
        session,
        models: list[str] | None,
        test_size: float,
        random_state: int,
        overrides: dict[str, dict[str, Any]] | None,
    ) -> dict[str, Any]:
        customers = session.query(Customer).all()
        if not customers:
            raise BizException(2001, "暂无客户数据", 404)
        dataframe = customers_dataframe(customers)
        features = prepare_features(dataframe)
        target = dataframe["Response"].astype(int)
        if target.nunique() < 2:
            raise BizException(3001, "训练数据必须包含两个类别", 500)
        x_train, x_test, y_train, y_test = train_test_split(
            features, target, test_size=test_size, random_state=random_state, stratify=target
        )
        scaler = StandardScaler()
        x_train_scaled = scaler.fit_transform(x_train)
        x_test_scaled = scaler.transform(x_test)
        selected = models or ["logistic_regression", "xgboost", "random_forest"]
        results: dict[str, dict[str, float]] = {}
        experiments: list[Experiment] = []
        for name in selected:
            supplied = (overrides or {}).get(name, {})
            estimator = self._get_model(name, y_train, supplied)
            estimator.fit(x_train_scaled, y_train)
            predicted = estimator.predict(x_test_scaled)
            probabilities = estimator.predict_proba(x_test_scaled)[:, 1]
            fpr, tpr, _ = roc_curve(y_test, probabilities)
            importance = (
                np.abs(estimator.coef_[0])
                if hasattr(estimator, "coef_")
                else estimator.feature_importances_
            )
            metrics = {
                "accuracy": float(accuracy_score(y_test, predicted)),
                "precision": float(precision_score(y_test, predicted, zero_division=0)),
                "recall": float(recall_score(y_test, predicted, zero_division=0)),
                "f1_score": float(f1_score(y_test, predicted, zero_division=0)),
                "roc_auc": float(roc_auc_score(y_test, probabilities)),
            }
            filename = f"{name}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S_%f')}.joblib"
            path = (settings.MODEL_DIR / filename).resolve()
            joblib.dump(
                {"model": estimator, "scaler": scaler, "feature_names": FEATURE_COLUMNS}, path
            )
            record = Experiment(
                model_name=name,
                **metrics,
                params={
                    "hyperparameters": supplied,
                    "roc": {"fpr": fpr.tolist(), "tpr": tpr.tolist()},
                    "confusion_matrix": confusion_matrix(y_test, predicted).tolist(),
                    "feature_importances": np.asarray(importance).tolist(),
                    "feature_names": FEATURE_COLUMNS,
                },
                model_path=str(path),
                is_best=False,
            )
            session.add(record)
            experiments.append(record)
            results[name] = metrics
        session.flush()
        session.query(Experiment).filter(Experiment.is_best.is_(True)).update(
            {Experiment.is_best: False}
        )
        winner = max(experiments, key=lambda item: item.roc_auc)
        winner.is_best = True
        session.commit()
        return {"best_model": winner.model_name, "results": results}

    @staticmethod
    def best_experiment(session) -> Experiment:
        experiment = (
            session.query(Experiment)
            .filter_by(is_best=True)
            .order_by(Experiment.created_at.desc())
            .first()
        )
        if experiment is None:
            raise BizException(3002, "无最佳模型", 400)
        return experiment

    def resolve_experiment(self, session, model_name: str | None) -> tuple[str, Path]:
        if model_name is None:
            experiment = self.best_experiment(session)
            return experiment.model_name, Path(experiment.model_path)
        experiment = (
            session.query(Experiment)
            .filter_by(model_name=model_name)
            .order_by(Experiment.created_at.desc())
            .first()
        )
        path = (
            Path(experiment.model_path)
            if experiment
            else (settings.MODEL_DIR / f"{model_name}.joblib")
        )
        if not path.is_file():
            raise BizException(3002, "模型文件不存在", 400)
        return model_name, path

    def predict_customers(self, session, model_name: str | None) -> tuple[str, int]:
        name, path = self.resolve_experiment(session, model_name)
        bundle = joblib.load(path)
        customers = session.query(Customer).order_by(Customer.id).all()
        if not customers:
            raise BizException(2001, "暂无客户数据", 404)
        features = prepare_features(customers_dataframe(customers))
        probabilities = bundle["model"].predict_proba(bundle["scaler"].transform(features))[:, 1]
        for customer, probability in zip(customers, probabilities, strict=True):
            customer.predicted_prob = float(probability)
        session.commit()
        return name, len(customers)

    def predict_dataframe(
        self, session, dataframe, model_name: str | None
    ) -> tuple[str, list[float]]:
        name, path = self.resolve_experiment(session, model_name)
        bundle = joblib.load(path)
        return name, bundle["model"].predict_proba(
            bundle["scaler"].transform(prepare_features(dataframe))
        )[:, 1].tolist()
