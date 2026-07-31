from sqlalchemy import desc

from app.core.response import BizException
from app.models import Customer, EmailRecord, PromptTemplate, User
from app.services.llm_service import LLMService


class EmailService:
    def __init__(self) -> None:
        self.llm = LLMService()

    @staticmethod
    def active_template(session) -> PromptTemplate:
        template = session.query(PromptTemplate).filter_by(is_active=True).first()
        if template is None:
            raise BizException(2001, "Prompt 模板不存在", 404)
        return template

    def targets(self, session, percentile: float, page: int, per_page: int) -> dict:
        if not 0 < percentile < 1:
            raise BizException(1001, "percentile 必须在 0 和 1 之间", 400)
        probabilities = [
            value[0]
            for value in session.query(Customer.predicted_prob)
            .filter(Customer.predicted_prob.is_not(None))
            .all()
        ]
        if not probabilities:
            raise BizException(3002, "暂无预测数据", 400)
        import numpy as np

        threshold = float(np.quantile(probabilities, percentile))
        query = (
            session.query(Customer)
            .filter(Customer.predicted_prob >= threshold)
            .order_by(desc(Customer.predicted_prob))
        )
        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        return {
            "threshold": threshold,
            "total": total,
            "customers": [
                {
                    "id": c.id,
                    "gender": c.gender,
                    "age": c.age,
                    "annual_premium": c.annual_premium,
                    "predicted_prob": c.predicted_prob,
                }
                for c in items
            ],
        }

    def generate(self, session, user: User, customer_ids: list[int] | None, limit: int) -> dict:
        if customer_ids:
            customers = session.query(Customer).filter(Customer.id.in_(customer_ids)).all()
            found = {customer.id for customer in customers}
            missing = set(customer_ids) - found
            if missing:
                raise BizException(2001, "部分客户不存在", 404)
        else:
            customers = (
                session.query(Customer)
                .filter(Customer.predicted_prob.is_not(None))
                .order_by(desc(Customer.predicted_prob))
                .limit(limit)
                .all()
            )
            if not customers:
                raise BizException(3002, "暂无预测数据", 400)
        template = self.active_template(session).content
        records = []
        generated = 0
        failed = 0
        for customer in customers:
            result = self.llm.generate_email(customer, template)
            record = EmailRecord(
                customer_id=customer.id,
                created_by=user.id,
                subject=result.get("subject", ""),
                content=result.get("content", result.get("error", "")),
                status="generated" if result["success"] else "failed",
            )
            session.add(record)
            session.flush()
            records.append(
                {"customer_id": customer.id, "status": record.status, "subject": record.subject}
            )
            generated += int(result["success"])
            failed += int(not result["success"])
        return {"generated_count": generated, "failed_count": failed, "records": records}
