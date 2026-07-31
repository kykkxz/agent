from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.core.response import BizException


class CredentialsRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=6, max_length=100)


class UpdateProfileRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)


class UpdatePasswordRequest(BaseModel):
    old_password: str = Field(min_length=6, max_length=100)
    new_password: str = Field(min_length=6, max_length=100)


class TrainRequest(BaseModel):
    models: list[str] | None = None
    test_size: float = Field(default=0.2, gt=0, lt=0.5)
    random_state: int = 42
    params: dict[str, dict[str, Any]] | None = None

    @field_validator("models")
    @classmethod
    def validate_models(cls, value: list[str] | None) -> list[str] | None:
        allowed = {"logistic_regression", "xgboost", "random_forest"}
        if value is not None and (not value or set(value) - allowed):
            raise ValueError("models 包含不支持的算法")
        return value


class PredictRequest(BaseModel):
    model_name: str | None = None


class GenerateEmailRequest(BaseModel):
    customer_ids: list[int] | None = None
    limit: int = Field(default=5, ge=1, le=100)


class PromptUpdateRequest(BaseModel):
    content: str = Field(min_length=20, max_length=10000)


class EmailUpdateRequest(BaseModel):
    email_subject: str | None = Field(default=None, max_length=300)
    email_content: str | None = Field(default=None, max_length=50000)


class EmailStatusRequest(BaseModel):
    status: str = Field(min_length=1, max_length=20)


class BatchDeleteRequest(BaseModel):
    record_ids: list[int] = Field(min_length=1, max_length=100)


def validate_request(model: type[BaseModel], payload: Any) -> BaseModel:
    try:
        return model.model_validate(payload or {})
    except ValidationError as error:
        raise BizException(1001, "参数校验错误", 400) from error
