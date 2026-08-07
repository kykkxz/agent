"""旅游规划智能分发系统入口。"""

from advisors import build_advisors
from planner import ask_advisors_concurrently, generate_plan
from router import build_router, dispatch


def interactive_mode() -> None:
    """启动交互式旅游问答。"""
    advisors = build_advisors()
    router = build_router()
    print("旅游规划智能分发系统已启动，输入 exit 退出。")

    while True:
        question = input("\n用户：").strip()
        if question.lower() == "exit":
            break

        advisor_names, _ = dispatch(router, question)
        if not advisor_names:
            print("主管未识别出需要参与的顾问，请补充更明确的旅行需求。")
            continue

        trip = {"destination": input("目的地：").strip(),
                "days": input("天数：").strip(),
                "budget": input("预算（元）：").strip()}
        answers = ask_advisors_concurrently(advisors, advisor_names, trip)
        for name in advisor_names:
            print(f"\n【{name}】")
            print(answers[name])


if __name__ == "__main__":
    while True:
        print("\n1. 交互式智能问答")
        print("2. 一键生成完整旅行计划")
        print("3. 退出")
        choice = input("请选择：").strip()
        if choice == "1":
            interactive_mode()
        elif choice == "2":
            destination = input("目的地：").strip()
            days = input("天数：").strip()
            budget = input("预算（元）：").strip()
            question = f"去{destination}玩{days}天，预算{budget}元，请生成完整旅行计划。"
            generate_plan(question, {"destination": destination, "days": days, "budget": budget})
        elif choice == "3":
            break
