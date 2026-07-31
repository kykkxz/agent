import json
import re
from typing import Any

from openai import OpenAI, OpenAIError

from app.core.config import settings
from app.models import Customer


class LLMService:
    def __init__(self) -> None:
        self.client = (
            OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_API_BASE)
            if settings.LLM_API_KEY
            else None
        )

    @staticmethod
    def profile(customer: Customer) -> dict[str, str | int | float]:
        return {
            "gender": "男性" if customer.gender == "Male" else "女性",
            "age": customer.age,
            "driving_license": "有" if customer.driving_license else "无",
            "vehicle_age": customer.vehicle_age,
            "vehicle_damage": "曾受损" if customer.vehicle_damage == "Yes" else "未受损",
            "annual_premium": customer.annual_premium,
        }

    def generate_email(self, customer: Customer, template: str) -> dict[str, Any]:
        if self.client is None:
            return {"success": False, "error": "LLM_API_KEY 未配置"}
        try:
            prompt = template.format(**self.profile(customer))
            response = self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            raw = (response.choices[0].message.content or "").strip()
            raw = re.sub(r"^```json\\s*", "", raw, flags=re.IGNORECASE)
            raw = re.sub(r"\\s*```$", "", raw)
            parsed = json.loads(raw)
            subject = parsed.get("subject")
            content = parsed.get("content")
            if not isinstance(subject, str) or not isinstance(content, str):
                raise TypeError("LLM 响应缺少 subject 或 content")
            return {"success": True, "subject": subject, "content": content}
        except (AttributeError, IndexError, KeyError, OpenAIError, TypeError, ValueError) as error:
            return {"success": False, "error": str(error)}
