from __future__ import annotations

import asyncio
import os
import random
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+aiomysql://root:123456@localhost:3306/job_db?charset=utf8mb4",
)

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class JobPost(Base):
    __tablename__ = "job_post"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    title: Mapped[str] = mapped_column(String(100), nullable=False, comment="职位名称")
    company: Mapped[str] = mapped_column(String(100), nullable=False, comment="公司名称")
    salary_min: Mapped[float] = mapped_column(Float, default=0, comment="最低薪资(k)")
    salary_max: Mapped[float] = mapped_column(Float, default=0, comment="最高薪资(k)")
    experience: Mapped[str] = mapped_column(String(50), default="不限", comment="经验要求")
    jd_text: Mapped[str | None] = mapped_column(Text, comment="职位描述原文")
    vector_id: Mapped[str | None] = mapped_column(String(100), comment="关联向量ID")
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")

    def __repr__(self) -> str:
        return f"<JobPost(title={self.title!r}, company={self.company!r})>"


def generate_jobs(count: int = 1000) -> list[JobPost]:
    titles = [
        "Python开发工程师",
        "Java后端工程师",
        "前端开发工程师",
        "数据分析师",
        "算法工程师",
        "测试开发工程师",
        "运维工程师",
        "产品经理",
        "数据库工程师",
        "全栈开发工程师",
    ]
    companies = [
        "字节跳动",
        "阿里巴巴",
        "腾讯",
        "百度",
        "美团",
        "京东",
        "小米",
        "网易",
        "快手",
        "拼多多",
    ]
    experiences = ["不限", "1年以内", "1-3年", "3-5年", "5年以上"]
    skills = ["Python", "Java", "Vue3", "TypeScript", "MySQL", "Redis", "Docker", "Kubernetes", "Spark", "TensorFlow"]
    random_generator = random.Random(20260721)

    jobs: list[JobPost] = []
    for index in range(1, count + 1):
        salary_min = random_generator.randint(8, 35)
        salary_max = salary_min + random_generator.randint(5, 25)
        title = random_generator.choice(titles)
        company = random_generator.choice(companies)
        selected_skills = "、".join(random_generator.sample(skills, k=3))
        jobs.append(
            JobPost(
                title=f"{title}-{index:04d}",
                company=company,
                salary_min=float(salary_min),
                salary_max=float(salary_max),
                experience=random_generator.choice(experiences),
                jd_text=f"负责{title}相关工作，要求熟悉{selected_skills}，具备良好的沟通能力和工程实践经验。",
                vector_id=f"job-vector-{index:04d}",
            )
        )

    return jobs


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("数据表创建成功！")


async def seed_jobs(count: int = 1000) -> None:
    async with AsyncSessionLocal() as db:
        db.add_all(generate_jobs(count))
        await db.commit()
        print(f"模拟岗位数据新增成功：{count}条")


async def query_jobs() -> list[JobPost]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(JobPost).order_by(JobPost.id))
        jobs = list(result.scalars().all())
        print(f"共{len(jobs)}条数据")
        for job in jobs[:10]:
            print(job)
        return jobs


async def main() -> None:
    await init_db()
    start = datetime.now()
    await seed_jobs()
    end = datetime.now()
    cost = (end - start).total_seconds()
    print(f"异步插入数据消耗{cost}s")
    print("\n查询岗位数据==========")
    await query_jobs()
    await engine.dispose()
    print("数据库引擎已关闭")


if __name__ == "__main__":
    asyncio.run(main())
