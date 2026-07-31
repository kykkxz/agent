from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    gender: Mapped[str] = mapped_column(String(10), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    driving_license: Mapped[int] = mapped_column(Integer, nullable=False)
    region_code: Mapped[float] = mapped_column(Float, nullable=False)
    previously_insured: Mapped[int] = mapped_column(Integer, nullable=False)
    vehicle_age: Mapped[str] = mapped_column(String(20), nullable=False)
    vehicle_damage: Mapped[str] = mapped_column(String(10), nullable=False)
    annual_premium: Mapped[float] = mapped_column(Float, nullable=False)
    policy_sales_channel: Mapped[float] = mapped_column(Float, nullable=False)
    vintage: Mapped[int] = mapped_column(Integer, nullable=False)
    response: Mapped[int] = mapped_column(Integer, nullable=False)
    predicted_prob: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
