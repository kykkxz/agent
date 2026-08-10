import os
from pathlib import Path
from textwrap import fill
from typing import TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph


load_dotenv()

llm = ChatOpenAI(
    model=os.getenv("MODEL_NAME"),  # type: ignore[reportArgumentType]
    api_key=os.getenv("API_KEY"),  # type: ignore[reportArgumentType]
    base_url=os.getenv("BASE_URL"),
    temperature=0.4,
)


class ProjectState(TypedDict):
    """在部门 Agent 之间流转的项目状态。"""

    topic: str
    marketing_plan: str
    ui_design: str
    frontend_code: str
    backend_code: str
    test_report: str
    delivery: str


def ask_ai(role: str, task: str) -> str:
    """调用部门 Agent，返回完整交付物用于下游流转。"""
    message = llm.invoke(
        f"你是IT系统开发公司的{role}。\n"
        f"{task}\n"
        "只输出交付物内容，不解释。"
    )
    return str(message.content).strip()


def marketing_agent(state: ProjectState) -> dict[str, str]:
    """营销部：根据主题输出营销方案。"""
    return {
        "marketing_plan": ask_ai(
            "营销部智能体",
            f"主题：{state['topic']}。生成一句营销方案。",
        )
    }


def ui_agent(state: ProjectState) -> dict[str, str]:
    """UI 设计部：结合主题和营销方案输出界面。"""
    return {
        "ui_design": ask_ai(
            "UI设计智能体",
            f"主题：{state['topic']}。营销方案：{state['marketing_plan']}。"
            "生成一句UI界面设计交付物。",
        )
    }


def frontend_agent(state: ProjectState) -> dict[str, str]:
    """前端部：根据主题和 UI 界面输出前端代码。"""
    return {
        "frontend_code": ask_ai(
            "前端开发智能体",
            f"主题：{state['topic']}。UI界面：{state['ui_design']}。"
            "生成一句前端代码交付物。",
        )
    }


def backend_agent(state: ProjectState) -> dict[str, str]:
    """后端部：根据主题和 UI 界面输出后端代码。"""
    return {
        "backend_code": ask_ai(
            "后端开发智能体",
            f"主题：{state['topic']}。UI界面：{state['ui_design']}。"
            "生成一句后端代码交付物。",
        )
    }


def testing_agent(state: ProjectState) -> dict[str, str]:
    """测试部：汇总前后端代码输出测试结果。"""
    return {
        "test_report": ask_ai(
            "测试智能体",
            f"前端代码：{state['frontend_code']}。后端代码：{state['backend_code']}。"
            "生成一句测试交付物。",
        )
    }


def project_manager_agent(state: ProjectState) -> dict[str, str]:
    """项目经理：汇总所有部门交付物并完成项目。"""
    department_outputs = (
        f"营销：{state['marketing_plan']}；"
        f"UI：{state['ui_design']}；"
        f"前端：{state['frontend_code']}；"
        f"后端：{state['backend_code']}；"
        f"测试：{state['test_report']}。"
    )
    return {
        "delivery": ask_ai(
            "项目经理智能体",
            f"主题：{state['topic']}。全部部门输出：{department_outputs}"
            "生成一句项目交付结论。",
        )
    }


def build_workflow():
    """构建营销、设计、研发、测试和项目管理协作图。"""
    workflow = StateGraph(ProjectState)

    workflow.add_node("marketing", marketing_agent)
    workflow.add_node("ui_design", ui_agent)
    workflow.add_node("frontend", frontend_agent)
    workflow.add_node("backend", backend_agent)
    workflow.add_node("testing", testing_agent)
    workflow.add_node("project_manager", project_manager_agent)

    workflow.add_edge(START, "marketing")
    workflow.add_edge("marketing", "ui_design")
    workflow.add_edge("ui_design", "frontend")
    workflow.add_edge("ui_design", "backend")
    workflow.add_edge(["frontend", "backend"], "testing")
    workflow.add_edge(
        ["marketing", "ui_design", "frontend", "backend", "testing"],
        "project_manager",
    )
    workflow.add_edge("project_manager", END)

    return workflow.compile()


def show_result(result: ProjectState) -> None:
    """以分段和自动换行的方式展示部门交付物。"""
    outputs = (
        ("营销部", result["marketing_plan"]),
        ("UI设计部", result["ui_design"]),
        ("前端部", result["frontend_code"]),
        ("后端部", result["backend_code"]),
        ("测试部", result["test_report"]),
        ("项目经理", result["delivery"]),
    )
    print("\n" + "=" * 42)
    print("IT 系统开发公司协作结果")
    print("=" * 42)
    print(f"\n项目主题：{result['topic']}")
    print("流程状态：所有部门已完成交付")

    for index, (department, output) in enumerate(outputs, start=1):
        print(f"\n{index}. {department}")
        print(fill(output, width=68, initial_indent="   ", subsequent_indent="   "))

    print("\n" + "=" * 42)
    print("项目流程已结束：END")
    print("=" * 42)


def main() -> None:
    """运行示例流程并输出 LangGraph 的 Mermaid 流程图。"""
    topic = input("请输入网站产品或线上系统主题：").strip() or "线上课程报名系统"
    workflow = build_workflow()

    print("\n=== LangGraph 流程图（Mermaid）===")
    print(workflow.get_graph().draw_mermaid())

    result = workflow.invoke({"topic": topic}) #type: ignore[reportArgumentType]
    show_result(result) #type: ignore[reportArgumentType]


if __name__ == "__main__":
    main()
