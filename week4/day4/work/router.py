"""主管节点：分析用户需求并决定需要哪些顾问参与。"""

import json
import re
from typing import Any

from langchain_core.runnables import Runnable
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from config import create_llm


ADVISOR_DESCRIPTIONS = {
    "destination": "目的地选择、景点、住宿、行程",
    "budget": "预算、花费、费用、价格、省钱",
    "transportation": "交通、机票、高铁、地铁、打车、通勤",
    "food": "美食、餐厅、小吃、吃饭、餐饮",
    "culture": "文化、历史、民俗、演出、礼仪、博物馆",
}


def build_router() -> Runnable[dict, Any]:
    """构建输出顾问名单和理由的 JSON Chain。"""
    parser = JsonOutputParser()
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是旅行问答系统的主管。根据用户需求，从以下顾问中选择需要参与的顾问："
                "destination（目的地）、budget（预算）、transportation（交通）、"
                "food（美食）、culture（文化）。\n{format_instructions}",
            ),
            ("human", "用户需求：{question}"),
        ]
    ).partial(format_instructions=parser.get_format_instructions())
    return prompt | create_llm() | parser


def dispatch(router: Runnable[dict, Any], question: str) -> tuple[list[str], str]:
    """分析用户问题，返回需要参与的顾问列表和分发决策说明。"""
    result = router.invoke({"question": question})
    advisors = result.get("advisors", [])
    reason = result.get("reason", "")

    if isinstance(advisors, str):
        advisors = [
            advisor.strip()
            for advisor in re.split(r"[,\s、，]+", advisors)
            if advisor.strip()
        ]

    valid = [advisor for advisor in advisors if advisor in ADVISOR_DESCRIPTIONS]
    decision = json.dumps(
        {
            "question": question,
            "advisors": valid,
            "reason": reason,
        },
        ensure_ascii=False,
        indent=2,
    )
    print("===== 分发决策 =====")
    print(decision)
    return valid, decision
