"""IT 系统开发公司的 LangGraph 多部门协作流程。"""

import os
from textwrap import fill
from typing import Any, Literal, TypedDict

from dotenv import load_dotenv
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel


load_dotenv()

llm = ChatOpenAI(
    model=os.getenv("MODEL_NAME"),  # type: ignore[reportArgumentType]
    api_key=os.getenv("API_KEY"),  # type: ignore[reportArgumentType]
    base_url=os.getenv("BASE_URL"),
    temperature=0.7,
)

MAX_RETRIES = 3
FORBIDDEN_TERMS = ("第一", "最好", "最好的", "最佳", "唯一", "顶级")


class AgentState(TypedDict):
    """在各部门 Agent 之间传递的项目状态。"""

    topic: str
    marketing_plan: str
    compliance_review: dict[str, Any]
    retry_count: int
    route: str
    ui_design: str
    frontend_code: str
    backend_code: str
    test_case: str
    final_report: str


class ComplianceReview(BaseModel):
    """合规审核部的结构化审核结果。"""

    decision: Literal["PASS", "REJECT"]
    matched_terms: list[str]
    reason: str


compliance_parser = JsonOutputParser(pydantic_object=ComplianceReview)
compliance_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是IT系统开发公司的合规审核部。\n"
            "审核营销方案是否包含绝对化、极限化宣传用语。\n"
            "重点检查：第一、最好、最好的、最佳、唯一、顶级。\n"
            "必须只返回合法 JSON，不要输出 Markdown 或额外解释。\n"
            "{format_instructions}",
        ),
        (
            "human",
            "网站产品主题：{topic}\n"
            "待审核营销方案：{marketing_plan}",
        ),
    ]
).partial(format_instructions=compliance_parser.get_format_instructions())
compliance_chain = compliance_prompt | llm | compliance_parser


def text_from_message(message: Any) -> str:
    """提取模型消息文本，不改变模型输出内容。"""
    return str(message.content).strip()


def marketing_agent(state: AgentState) -> dict[str, Any]:
    """营销部：生成方案，审核驳回后根据意见重写。"""
    attempt = state.get("retry_count", 0) + 1
    review = state.get("compliance_review", {})
    feedback = "首次生成，无历史审核意见。"
    if review:
        feedback = (
            f"上次审核结果：{review.get('decision')}；"
            f"命中词语：{review.get('matched_terms', [])}；"
            f"审核意见：{review.get('reason', '')}。"
            "请避开命中词语并重新生成。"
        )

    prompt = ChatPromptTemplate.from_template(
        "你是IT系统开发公司的营销部智能体。\n"
        "请为【{topic}】设计一份真实、克制、合规的营销方案。\n"
        "{feedback}\n"
        "只输出营销方案正文。"
    )
    response = (prompt | llm).invoke(
        {"topic": state["topic"], "feedback": feedback}
    )
    print(f"[营销部] 第 {attempt} 次提交营销方案")
    return {
        "marketing_plan": text_from_message(response),
        "retry_count": attempt,
    }


def reviewer_agent(state: AgentState) -> dict[str, Any]:
    """合规审核部：使用 JsonOutputParser 生成结构化审核结果。"""
    parsed = compliance_chain.invoke(
        {
            "topic": state["topic"],
            "marketing_plan": state["marketing_plan"],
        }
    )
    review = ComplianceReview.model_validate(parsed)

    # 绝对化词语属于硬规则，不能只依赖模型自行判断。
    matched_terms = [
        term for term in FORBIDDEN_TERMS if term in state["marketing_plan"]
    ]
    if matched_terms:
        review = review.model_copy(
            update={
                "decision": "REJECT",
                "matched_terms": matched_terms,
                "reason": "方案包含禁止的绝对化宣传用语。",
            }
        )

    print(
        f"[合规审核部] {review.decision}"
        f"，命中词语：{review.matched_terms or '无'}"
    )
    return {"compliance_review": review.model_dump()}


def review_router_agent(state: AgentState) -> dict[str, str]:
    """审核路由：通过、重试或进入兜底方案。"""
    review = ComplianceReview.model_validate(state["compliance_review"])
    if review.decision == "PASS":
        route = "PASS"
    elif state.get("retry_count", 0) < MAX_RETRIES:
        route = "RETRY"
    else:
        route = "FALLBACK"

    print(f"[review_router] {route}")
    return {"route": route}


def route_after_review(state: AgentState) -> str:
    """返回条件边使用的路由名称。"""
    return state["route"]


def fallback_agent(state: AgentState) -> dict[str, Any]:
    """兜底生成固定的合规营销方案，不再次调用模型。"""
    fallback_plan = (
        "围绕用户需求，突出产品功能、服务体验和实际应用价值，"
        "帮助目标用户了解并使用系统。"
    )
    print("[fallback] 使用固定合规营销方案")
    return {
        "marketing_plan": fallback_plan,
        "compliance_review": ComplianceReview(
            decision="PASS",
            matched_terms=[],
            reason="已使用固定兜底方案。",
        ).model_dump(),
    }


def ui_agent(state: AgentState) -> dict[str, str]:
    """UI 设计部：基于最终合规方案设计界面。"""
    prompt = ChatPromptTemplate.from_template(
        "你是UI设计部智能体。\n"
        "产品主题：{topic}\n"
        "最终营销方案：{marketing_plan}\n"
        "请输出页面结构、信息层级和视觉方向，不能直接复述营销文案。"
    )
    response = (prompt | llm).invoke(
        {
            "topic": state["topic"],
            "marketing_plan": state["marketing_plan"],
        }
    )
    print("[UI设计部] 开始设计界面")
    return {"ui_design": text_from_message(response)}


def frontend_agent(state: AgentState) -> dict[str, str]:
    """前端部：结合 UI 设计输出前端实现方案。"""
    prompt = ChatPromptTemplate.from_template(
        "你是前端开发智能体。\n"
        "产品主题：{topic}\n"
        "UI设计方案：{ui_design}\n"
        "请输出前端页面、交互和技术实现方案。"
    )
    response = (prompt | llm).invoke(
        {"topic": state["topic"], "ui_design": state["ui_design"]}
    )
    print("[前端部] 开始实现前端")
    return {"frontend_code": text_from_message(response)}


def backend_agent(state: AgentState) -> dict[str, str]:
    """后端部：结合 UI 设计输出后端实现方案。"""
    prompt = ChatPromptTemplate.from_template(
        "你是后端开发智能体。\n"
        "产品主题：{topic}\n"
        "UI设计方案：{ui_design}\n"
        "请输出后端接口、数据模型和安全设计方案。"
    )
    response = (prompt | llm).invoke(
        {"topic": state["topic"], "ui_design": state["ui_design"]}
    )
    print("[后端部] 开始实现后端")
    return {"backend_code": text_from_message(response)}


def test_agent(state: AgentState) -> dict[str, str]:
    """测试部：等待前后端完成后制定联调测试方案。"""
    prompt = ChatPromptTemplate.from_template(
        "你是测试部智能体。\n"
        "产品主题：{topic}\n"
        "前端实现：{frontend_code}\n"
        "后端实现：{backend_code}\n"
        "请输出覆盖核心流程、权限和数据安全的测试方案。"
    )
    response = (prompt | llm).invoke(
        {
            "topic": state["topic"],
            "frontend_code": state["frontend_code"],
            "backend_code": state["backend_code"],
        }
    )
    print("[测试部] 开始联调测试")
    return {"test_case": text_from_message(response)}


def summarizer_agent(state: AgentState) -> dict[str, str]:
    """项目经理：汇总所有部门输出形成最终报告。"""
    prompt = ChatPromptTemplate.from_template(
        "你是项目经理智能体。请汇总以下项目交付物，形成最终项目报告。\n"
        "产品主题：{topic}\n"
        "营销方案：{marketing_plan}\n"
        "合规审核：{compliance_review}\n"
        "UI设计：{ui_design}\n"
        "前端实现：{frontend_code}\n"
        "后端实现：{backend_code}\n"
        "测试方案：{test_case}\n"
        "请按模块分段输出，包含项目状态和后续交付结论。"
    )
    response = (prompt | llm).invoke(
        {
            "topic": state["topic"],
            "marketing_plan": state["marketing_plan"],
            "compliance_review": state["compliance_review"],
            "ui_design": state["ui_design"],
            "frontend_code": state["frontend_code"],
            "backend_code": state["backend_code"],
            "test_case": state["test_case"],
        }
    )
    print("[项目经理] 正在整理最终报告")
    return {"final_report": text_from_message(response)}


def show_result(result: AgentState) -> None:
    """以分段方式展示最终审核和项目报告。"""
    review = ComplianceReview.model_validate(result["compliance_review"])
    print("\n" + "=" * 48)
    print("IT 系统开发公司协作结果")
    print("=" * 48)
    print(f"\n项目主题：{result['topic']}")
    print(f"营销方案尝试次数：{result.get('retry_count', 0)}")
    print(f"合规审核：{review.decision}（{review.reason}）")
    print(f"命中词语：{review.matched_terms or '无'}")
    print("\n最终项目报告：")
    print(fill(result["final_report"], width=72, initial_indent="   ", subsequent_indent="   "))
    print("\n" + "=" * 48)
    print("项目流程已结束：END")
    print("=" * 48)


def build_complex_dependency_graph():
    """构建带审核循环、并行开发和最终汇总的 LangGraph。"""
    workflow = StateGraph(AgentState)

    workflow.add_node("marketing", marketing_agent)
    workflow.add_node("reviewer", reviewer_agent)
    workflow.add_node("review_router", review_router_agent)
    workflow.add_node("fallback", fallback_agent)
    workflow.add_node("ui", ui_agent)
    workflow.add_node("frontend", frontend_agent)
    workflow.add_node("backend", backend_agent)
    workflow.add_node("test", test_agent)
    workflow.add_node("summarizer", summarizer_agent)

    workflow.add_edge(START, "marketing")
    workflow.add_edge("marketing", "reviewer")
    workflow.add_edge("reviewer", "review_router")
    workflow.add_conditional_edges(
        "review_router",
        route_after_review,
        {
            "PASS": "ui",
            "RETRY": "marketing",
            "FALLBACK": "fallback",
        },
    )
    workflow.add_edge("fallback", "ui")
    workflow.add_edge("ui", "frontend")
    workflow.add_edge("ui", "backend")
    workflow.add_edge(["frontend", "backend"], "test")
    workflow.add_edge("test", "summarizer")
    workflow.add_edge("summarizer", END)

    return workflow.compile()


if __name__ == "__main__":
    app = build_complex_dependency_graph()
    topic = input("请输入网站产品或线上系统主题：").strip() or "线上课程报名系统"

    print("\n=== LangGraph 流程图（Mermaid）===")
    print(app.get_graph().draw_mermaid())

    result = app.invoke(
        {
            "topic": topic,
            "marketing_plan": "",
            "compliance_review": {},
            "retry_count": 0,
            "route": "",
            "ui_design": "",
            "frontend_code": "",
            "backend_code": "",
            "test_case": "",
            "final_report": "",
        }
    )
    show_result(result) #type: ignore[reportArgumentType]
