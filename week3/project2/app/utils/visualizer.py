import base64
from io import BytesIO

import matplotlib

matplotlib.use("Agg")
import pandas as pd
from matplotlib.figure import Figure

from app.core.response import BizException


def _image(figure: Figure) -> str:
    buffer = BytesIO()
    figure.tight_layout()
    figure.savefig(buffer, format="png", dpi=120)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def data_chart(chart_type: str, dataframe: pd.DataFrame) -> str:
    figure = Figure(figsize=(7, 4))
    axis = figure.subplots()
    if chart_type == "response_distribution":
        dataframe["Response"].value_counts().sort_index().plot.bar(
            ax=axis, color=["#5e8271", "#d17a4b"]
        )
        axis.set_xlabel("Response")
    elif chart_type == "gender_response":
        pd.crosstab(dataframe["Gender"], dataframe["Response"]).plot.bar(
            ax=axis, color=["#5e8271", "#d17a4b"]
        )
    elif chart_type == "age_distribution":
        dataframe["Age"].plot.hist(ax=axis, bins=25, color="#5e8271")
    elif chart_type == "premium_distribution":
        dataframe["Annual_Premium"].plot.hist(ax=axis, bins=30, color="#d17a4b")
    else:
        raise BizException(1001, "未知图表类型", 400)
    return _image(figure)


def model_chart(chart_type: str, experiments, model_name: str | None = None) -> str:
    figure = Figure(figsize=(7, 4))
    axis = figure.subplots()
    if chart_type == "metrics_comparison":
        labels = [item.model_name for item in experiments]
        axis.bar(labels, [item.roc_auc for item in experiments], color="#5e8271")
        axis.set_ylabel("ROC-AUC")
    else:
        target = next((item for item in experiments if item.model_name == model_name), None)
        if target is None:
            raise BizException(2001, "模型实验不存在", 404)
        data = target.params
        if chart_type == "roc_curve":
            roc = data.get("roc", {})
            axis.plot(roc.get("fpr", []), roc.get("tpr", []), color="#d17a4b")
            axis.plot([0, 1], [0, 1], "--", color="#666")
            axis.set_xlabel("False Positive Rate")
            axis.set_ylabel("True Positive Rate")
        elif chart_type == "confusion_matrix":
            image = axis.imshow(data.get("confusion_matrix", [[0, 0], [0, 0]]), cmap="Greens")
            figure.colorbar(image, ax=axis)
        elif chart_type == "feature_importance":
            features = data.get("feature_names", [])
            values = data.get("feature_importances", [])
            axis.barh(features, values, color="#5e8271")
        else:
            raise BizException(1001, "未知图表类型", 400)
    return _image(figure)
