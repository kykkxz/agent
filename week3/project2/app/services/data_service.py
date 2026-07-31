from typing import Any

import pandas as pd
from sqlalchemy import String, cast, delete, func

from app.models import Customer
from app.services.common import customer_out, paginate
from app.utils.data_processor import REQUIRED_COLUMNS, parse_excel


class DataService:
    def read_excel(self, file_storage: Any, require_response: bool = True) -> pd.DataFrame:
        return pd.DataFrame(parse_excel(file_storage, require_response=require_response))

    @staticmethod
    def quality_report(dataframe: pd.DataFrame) -> dict[str, Any]:
        return {
            "total_rows": len(dataframe),
            "total_cols": len(dataframe.columns),
            "missing_values": {key: int(value) for key, value in dataframe.isna().sum().items()},
            "duplicates": int(dataframe.duplicated().sum()),
            "dtypes": {key: str(value) for key, value in dataframe.dtypes.items()},
        }

    def replace_customers(self, session, dataframe: pd.DataFrame) -> int:
        mapping = {
            "Gender": "gender",
            "Age": "age",
            "Driving_License": "driving_license",
            "Region_Code": "region_code",
            "Previously_Insured": "previously_insured",
            "Vehicle_Age": "vehicle_age",
            "Vehicle_Damage": "vehicle_damage",
            "Annual_Premium": "annual_premium",
            "Policy_Sales_Channel": "policy_sales_channel",
            "Vintage": "vintage",
            "Response": "response",
        }
        records = [
            {"id": row["id"], **{target: row[name] for name, target in mapping.items()}}
            for row in dataframe.to_dict(orient="records")
        ]
        session.execute(delete(Customer))
        for start in range(0, len(records), 5000):
            chunk = records[start : start + 5000]
            session.bulk_insert_mappings(Customer, chunk)
        session.commit()
        return len(dataframe)

    @staticmethod
    def list_customers(
        session,
        page: int,
        per_page: int,
        gender: str | None = None,
        age_min: int | None = None,
        age_max: int | None = None,
        previously_insured: int | None = None,
        keyword: str | None = None,
    ) -> dict[str, Any]:
        query = session.query(Customer)
        if gender:
            query = query.filter(Customer.gender == gender)
        if age_min is not None:
            query = query.filter(Customer.age >= age_min)
        if age_max is not None:
            query = query.filter(Customer.age <= age_max)
        if previously_insured is not None:
            query = query.filter(Customer.previously_insured == previously_insured)
        if keyword:
            query = query.filter(cast(Customer.id, String).contains(keyword))
        return paginate(query.order_by(Customer.id), page, per_page, customer_out)

    @staticmethod
    def statistics(session) -> dict[str, Any]:
        total = session.query(func.count(Customer.id)).scalar() or 0
        gender_rows = (
            session.query(Customer.gender, func.count(Customer.id)).group_by(Customer.gender).all()
        )
        response_rows = (
            session.query(Customer.response, func.count(Customer.id))
            .group_by(Customer.response)
            .all()
        )
        age = session.query(
            func.min(Customer.age), func.max(Customer.age), func.avg(Customer.age)
        ).one()
        return {
            "total": total,
            "gender_distribution": {name: count for name, count in gender_rows},
            "response_distribution": {str(name): count for name, count in response_rows},
            "age_stats": {"min": age[0], "max": age[1], "avg": float(age[2]) if age[2] else None},
        }

    @staticmethod
    def current_quality(session) -> dict[str, Any]:
        count = session.query(func.count(Customer.id)).scalar() or 0
        return {
            "total_rows": count,
            "total_cols": len(REQUIRED_COLUMNS),
            "missing_values": {column: 0 for column in REQUIRED_COLUMNS},
            "duplicates": 0,
            "dtypes": {column: "database" for column in REQUIRED_COLUMNS},
        }
