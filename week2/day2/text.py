import asyncio
import time
from collections.abc import Iterable
from statistics import mean

from sqlalchemy import Column, Float, Integer, String, Text, create_engine, delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


COUNT = 10000
RUNS = 3


SYNC_DATABASE_URL = "mysql+pymysql://root:123456@localhost:3306/job_db?charset=utf8mb4"
ASYNC_DATABASE_URL = "mysql+aiomysql://root:123456@localhost:3306/job_db?charset=utf8mb4"

sync_engine = create_engine(SYNC_DATABASE_URL, echo=False)
async_engine = create_async_engine(ASYNC_DATABASE_URL, echo=False)

SyncSessionLocal = sessionmaker(bind=sync_engine, autoflush=False, expire_on_commit=False)
AsyncSessionLocal = async_sessionmaker(bind=async_engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class SyncJob(Base):
    __tablename__ = "sync_job"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(100), nullable=False)
    company = Column(String(100), nullable=False)
    salary_min = Column(Float, default=0)
    salary_max = Column(Float, default=0)
    experience = Column(String(50), default="不限")
    jd_text = Column(Text)


class AsyncJob(Base):
    __tablename__ = "async_job"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(100), nullable=False)
    company = Column(String(100), nullable=False)
    salary_min = Column(Float, default=0)
    salary_max = Column(Float, default=0)
    experience = Column(String(50), default="不限")
    jd_text = Column(Text)


def PerfJob(title, company, salary_min, salary_max, experience,jd_text):
    return {
        "title": title,
        "company": company,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "experience": experience,
        "jd_text": jd_text,
    }


def generate_jobs(count: int = COUNT) -> list[dict[str, object]]:
    """模拟 JD 数据"""
    companies = ["字节", "阿里", "腾讯", "美团", "京东", "百度", "网易", "快手"]
    titles = ["Python开发", "Java开发", "前端开发", "算法工程师", "测试开发", "运维工程师"]
    experiences = ["1-3年", "3-5年", "5年以上", "不限"]
    jd_templates = [
        "岗位{i}：需要掌握Python、MySQL、Redis等技术，有Web开发经验优先...",
        "岗位{i}：负责Java微服务开发，熟悉Spring Cloud、Docker、K8s...",
        "岗位{i}：负责前端产品迭代，精通Vue3/React、TypeScript...",
        "岗位{i}：负责推荐算法优化，熟悉机器学习、深度学习框架...",
    ]
    jobs = []
    for i in range(count):
        jobs.append(PerfJob(
            title=f"{titles[i % len(titles)]}-{i}",
            company=f"{companies[i % len(companies)]}-部门{i}",
            salary_min=10 + (i % 25),
            salary_max=20 + (i % 30),
            experience=experiences[i % len(experiences)],
            jd_text=jd_templates[i % len(jd_templates)].format(i=i)
        ))
    return jobs


def build_sync_jobs(rows: Iterable[dict[str, object]]) -> list[SyncJob]:
    return [SyncJob(**row) for row in rows]


def build_async_jobs(rows: Iterable[dict[str, object]]) -> list[AsyncJob]:
    return [AsyncJob(**row) for row in rows]


def init_sync_table() -> None:
    Base.metadata.create_all(bind=sync_engine)


async def init_async_table() -> None:
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def clear_sync_jobs() -> None:
    with SyncSessionLocal() as session:
        session.execute(delete(SyncJob))
        session.commit()


async def clear_async_jobs() -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(delete(AsyncJob))
        await session.commit()


def insert_sync_jobs(rows: list[dict[str, object]]) -> float:
    clear_sync_jobs()
    start = time.perf_counter()

    with SyncSessionLocal() as session:
        session.add_all(build_sync_jobs(rows))
        session.commit()

    return time.perf_counter() - start


async def insert_async_jobs(rows: list[dict[str, object]]) -> float:
    await clear_async_jobs()
    start = time.perf_counter()

    async with AsyncSessionLocal() as session:
        session.add_all(build_async_jobs(rows))
        await session.commit()

    return time.perf_counter() - start


def count_sync_jobs() -> int:
    with SyncSessionLocal() as session:
        return len(session.scalars(select(SyncJob)).all())


async def count_async_jobs() -> int:
    async with AsyncSessionLocal() as session:
        result = await session.scalars(select(AsyncJob))
        return len(result.all())


async def main() -> None:
    rows = generate_jobs(COUNT)

    init_sync_table()
    await init_async_table()

    sync_seconds_list = []
    async_seconds_list = []

    for _ in range(RUNS):
        sync_seconds_list.append(insert_sync_jobs(rows))
        async_seconds_list.append(await insert_async_jobs(rows))

    sync_seconds = mean(sync_seconds_list)
    async_seconds = mean(async_seconds_list)

    sync_count = count_sync_jobs()
    async_count = await count_async_jobs()

    print(f"固定模板数据：{COUNT} 条，重复运行：{RUNS} 次")
    print(f"同步写入 {sync_count} 条数据，平均用时：{sync_seconds:.4f} 秒")
    print(f"异步写入 {async_count} 条数据，平均用时：{async_seconds:.4f} 秒")
    print(f"异步/同步耗时比：{async_seconds / sync_seconds:.2f}")

    await async_engine.dispose()
    sync_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
