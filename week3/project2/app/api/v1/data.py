from flask import Blueprint, request

from app.core.database import get_db
from app.core.dependencies import login_required
from app.core.response import BizException, success
from app.models import Customer
from app.services.data_service import DataService
from app.utils.data_processor import customers_dataframe
from app.utils.visualizer import data_chart

bp = Blueprint("data", __name__, url_prefix="/api/v1/data")
service = DataService()


def _integer_query(name: str, default: int | None = None) -> int | None:
    value = request.args.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as error:
        raise BizException(1001, f"{name} 必须为整数", 400) from error


@bp.post("/upload")
@login_required
def upload():
    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        raise BizException(1001, "未上传文件", 400)
    if not uploaded.filename.lower().endswith((".xlsx", ".xls")):
        raise BizException(1001, "仅支持 Excel 文件", 400)
    dataframe = service.read_excel(uploaded)
    report = service.quality_report(dataframe)
    count = service.replace_customers(get_db(), dataframe)
    return success({"imported_count": count, "quality_report": report})


@bp.get("/customers")
@login_required
def customers():
    age_min = _integer_query("age_min")
    age_max = _integer_query("age_max")
    insured = _integer_query("previously_insured")
    return success(
        service.list_customers(
            get_db(),
            _integer_query("page", 1) or 1,
            _integer_query("per_page", 50) or 50,
            gender=request.args.get("gender"),
            age_min=age_min,
            age_max=age_max,
            previously_insured=insured,
            keyword=request.args.get("keyword"),
        )
    )


@bp.get("/statistics")
@login_required
def statistics():
    return success(service.statistics(get_db()))


@bp.get("/quality")
@login_required
def quality():
    return success(service.current_quality(get_db()))


@bp.get("/visualization/<chart_type>")
@login_required
def visualization(chart_type: str):
    customers = get_db().query(Customer).all()
    if not customers:
        raise BizException(2001, "暂无客户数据", 404)
    dataframe = customers_dataframe(customers)
    return success(
        {
            "chart_type": chart_type,
            "image_base64": data_chart(chart_type, dataframe),
            "format": "png",
        }
    )
