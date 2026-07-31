from pathlib import Path

from flask import Blueprint, g, request, send_file
from werkzeug.utils import secure_filename

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import login_required, role_required
from app.core.response import BizException, success
from app.models import Experiment
from app.schemas import PredictRequest, TrainRequest, validate_request
from app.services.common import experiment_out, log_operation, paginate
from app.services.data_service import DataService
from app.services.ml_service import MLService
from app.utils.visualizer import model_chart

bp = Blueprint("model", __name__, url_prefix="/api/v1/model")
service = MLService()
data_service = DataService()


def _page(name: str, default: int) -> int:
    try:
        return int(request.args.get(name, default))
    except ValueError as error:
        raise BizException(1001, f"{name} 必须为整数", 400) from error


@bp.post("/train")
@role_required("admin")
def train():
    payload = validate_request(TrainRequest, request.get_json(silent=True))
    session = get_db()
    try:
        result = service.train(
            session, payload.models, payload.test_size, payload.random_state, payload.params
        )
    except BizException:
        raise
    except Exception as error:
        session.rollback()
        raise BizException(3001, "训练失败", 500) from error
    log_operation(
        session, g.current_user.id, "model_training", f"best_model={result['best_model']}"
    )
    session.commit()
    return success(result)


@bp.get("/experiments")
@login_required
def experiments():
    query = get_db().query(Experiment)
    model_name = request.args.get("model_name")
    if model_name:
        query = query.filter_by(model_name=model_name)
    return success(
        paginate(
            query.order_by(Experiment.created_at.desc()),
            _page("page", 1),
            _page("per_page", 50),
            experiment_out,
        )
    )


@bp.get("/best")
@login_required
def best():
    experiment = service.best_experiment(get_db())
    return success(
        {
            "model_name": experiment.model_name,
            "roc_auc": experiment.roc_auc,
            "experiment_id": experiment.id,
        }
    )


@bp.post("/predict")
@login_required
def predict():
    payload = validate_request(PredictRequest, request.get_json(silent=True))
    session = get_db()
    try:
        model_name, count = service.predict_customers(session, payload.model_name)
    except BizException:
        raise
    except Exception as error:
        session.rollback()
        raise BizException(3002, "预测失败", 500) from error
    log_operation(session, g.current_user.id, "prediction", f"model={model_name}; count={count}")
    session.commit()
    return success({"model_name": model_name, "predicted_count": count})


@bp.post("/predict_upload")
@login_required
def predict_upload():
    uploaded = request.files.get("file")
    if (
        uploaded is None
        or not uploaded.filename
        or not uploaded.filename.lower().endswith((".xlsx", ".xls"))
    ):
        raise BizException(1001, "请上传 Excel 文件", 400)
    dataframe = data_service.read_excel(uploaded.read(), require_response=False)
    model_name, probabilities = service.predict_dataframe(
        get_db(), dataframe, request.form.get("model")
    )
    predictions = [
        {"id": int(row.id), "predicted_prob": float(probability)}
        for row, probability in zip(dataframe.itertuples(), probabilities, strict=True)
    ]
    return success(
        {
            "model_name": model_name,
            "total_count": len(predictions),
            "statistics": {
                "min": min(probabilities),
                "max": max(probabilities),
                "avg": sum(probabilities) / len(probabilities),
            },
            "predictions": predictions,
        }
    )


@bp.get("/visualization/<chart_type>")
@login_required
def visualization(chart_type: str):
    session = get_db()
    experiments = session.query(Experiment).order_by(Experiment.created_at.desc()).all()
    if not experiments:
        raise BizException(2001, "暂无实验记录", 404)
    name = request.args.get("model")
    if chart_type in {"roc_curve", "confusion_matrix", "feature_importance"} and not name:
        raise BizException(1001, "该图表需要 model 参数", 400)
    return success(
        {
            "chart_type": chart_type,
            "image_base64": model_chart(chart_type, experiments, name),
            "format": "png",
        }
    )


@bp.get("/export/<model_name>")
@role_required("admin")
def export_model(model_name: str):
    _, path = service.resolve_experiment(get_db(), model_name)
    return send_file(path, as_attachment=True, download_name=path.name)


@bp.post("/import")
@role_required("admin")
def import_model():
    uploaded = request.files.get("file")
    if (
        uploaded is None
        or not uploaded.filename
        or not uploaded.filename.lower().endswith(".joblib")
    ):
        raise BizException(1001, "请上传 .joblib 模型文件", 400)
    filename = secure_filename(uploaded.filename)
    if not filename:
        raise BizException(1001, "非法文件名", 400)
    path = (settings.MODEL_DIR / filename).resolve()
    if path.parent != settings.MODEL_DIR.resolve():
        raise BizException(1001, "非法文件名", 400)
    uploaded.save(path)
    log_operation(get_db(), g.current_user.id, "model_import", f"path={path}")
    get_db().commit()
    return success({"model_name": Path(filename).stem, "path": str(path)})
