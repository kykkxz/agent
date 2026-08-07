"""旅行计划生成器：单顾问、并发顾问和完整旅行计划。"""

from concurrent.futures import ThreadPoolExecutor, as_completed

from advisors import build_advisors
from langchain_core.runnables import Runnable
from router import ADVISOR_DESCRIPTIONS, build_router, dispatch


def ask_single_advisor(
    advisors: dict[str, Runnable[dict, str]],
    advisor_name: str,
    trip: dict,
) -> str:
    """调用单个顾问并返回回答。"""
    chain = advisors[advisor_name]
    return chain.invoke(trip)


def ask_advisors_concurrently(
    advisors: dict[str, Runnable[dict, str]],
    advisor_names: list[str],
    trip: dict,
) -> dict[str, str]:
    """并发调用多个顾问，返回顾问名称到回答的映射。"""
    answers = {}
    with ThreadPoolExecutor(max_workers=len(advisor_names)) as executor:
        futures = {
            executor.submit(ask_single_advisor, advisors, name, trip): name
            for name in advisor_names
        }
        for future in as_completed(futures):
            name = futures[future]
            answers[name] = future.result()
    return answers


def generate_plan(question: str, trip: dict) -> None:
    """打印分发决策，并并发调用全部顾问生成完整旅行计划。"""
    advisors = build_advisors()
    router = build_router()
    dispatch(router, question)
    advisor_names = list(ADVISOR_DESCRIPTIONS)
    print("\n===== 计划分发决策 =====")
    print("完整旅行计划：并发调用 destination、budget、transportation、food、culture")

    answers = ask_advisors_concurrently(advisors, advisor_names, trip)
    print("\n===== 顾问回答 =====")
    for name in advisor_names:
        print(f"\n【{ADVISOR_DESCRIPTIONS[name]}】")
        print(answers[name])

    print("\n===== 完整旅行计划 =====")
    print(f"目的地：{trip['destination']}")
    print(f"天数：{trip['days']} 天")
    print(f"预算：{trip['budget']} 元")
    for name in advisor_names:
        print(f"\n{name} 建议：")
        print(answers[name])
