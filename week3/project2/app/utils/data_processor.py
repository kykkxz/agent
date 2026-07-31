from io import BytesIO
from typing import Any

import pandas as pd

from app.core.response import BizException

FEATURE_COLUMNS = [
    "Gender",
    "Age",
    "Driving_License",
    "Region_Code",
    "Previously_Insured",
    "Vehicle_Age",
    "Vehicle_Damage",
    "Annual_Premium",
    "Policy_Sales_Channel",
    "Vintage",
]

REQUIRED_COLUMNS = [
    "id",
    "Gender",
    "Age",
    "Driving_License",
    "Region_Code",
    "Previously_Insured",
    "Vehicle_Age",
    "Vehicle_Damage",
    "Annual_Premium",
    "Policy_Sales_Channel",
    "Vintage",
    "Response",
]

INTEGER_COLUMNS = {"id", "Age", "Driving_License", "Previously_Insured", "Vintage", "Response"}
FLOAT_COLUMNS = {"Region_Code", "Annual_Premium", "Policy_Sales_Channel"}
TEXT_COLUMNS = {"Gender", "Vehicle_Age", "Vehicle_Damage"}


def parse_excel(file_storage: Any, require_response: bool = True) -> list[dict[str, Any]]:
    source = file_storage
    if isinstance(source, (bytes, bytearray)):
        source = BytesIO(source)
    elif hasattr(source, "stream"):
        source = source.stream

    try:
        dataframe = pd.read_excel(source)
    except Exception as error:
        raise BizException(2002, "Excel 解析失败", 400) from error

    required = REQUIRED_COLUMNS if require_response else REQUIRED_COLUMNS[:-1]
    missing = sorted(set(required) - set(dataframe.columns))
    if missing:
        raise BizException(1001, f"缺少必需字段: {', '.join(missing)}", 400)

    errors: list[str] = []
    records: list[dict[str, Any]] = []
    for row_number, (_, row) in enumerate(dataframe[required].iterrows(), start=2):
        record = row.to_dict()
        for column in required:
            value = record[column]
            if pd.isna(value):
                errors.append(f"第 {row_number} 行 {column} 为空")
                continue
            if column in INTEGER_COLUMNS:
                number = pd.to_numeric(value, errors="coerce")
                if pd.isna(number) or not float(number).is_integer():
                    errors.append(f"第 {row_number} 行 {column} 必须为整数")
                else:
                    record[column] = int(number)
            elif column in FLOAT_COLUMNS:
                number = pd.to_numeric(value, errors="coerce")
                if pd.isna(number):
                    errors.append(f"第 {row_number} 行 {column} 必须为数字")
                else:
                    record[column] = float(number)
            elif column in TEXT_COLUMNS:
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"第 {row_number} 行 {column} 必须为非空文本")
                else:
                    record[column] = value.strip()
        records.append(record)

    if errors:
        error = BizException(2002, f"Excel 解析失败: {'；'.join(errors)}", 400)
        error.errors = errors
        raise error
    return records


def prepare_features(dataframe: pd.DataFrame) -> pd.DataFrame:
    frame = dataframe[FEATURE_COLUMNS].copy()
    frame["Gender"] = frame["Gender"].map({"Male": 0, "Female": 1})
    frame["Vehicle_Damage"] = frame["Vehicle_Damage"].map({"No": 0, "Yes": 1})
    frame["Vehicle_Age"] = frame["Vehicle_Age"].map({"< 1 Year": 0, "1-2 Year": 1, "> 2 Years": 2})
    if frame.isna().any().any():
        raise BizException(1001, "特征字段含不支持的取值", 400)
    return frame.astype(float)


def customers_dataframe(customers) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Gender": customer.gender,
                "Age": customer.age,
                "Driving_License": customer.driving_license,
                "Region_Code": customer.region_code,
                "Previously_Insured": customer.previously_insured,
                "Vehicle_Age": customer.vehicle_age,
                "Vehicle_Damage": customer.vehicle_damage,
                "Annual_Premium": customer.annual_premium,
                "Policy_Sales_Channel": customer.policy_sales_channel,
                "Vintage": customer.vintage,
                "Response": customer.response,
            }
            for customer in customers
        ]
    )
