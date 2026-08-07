"""旅行顾问 Chain 定义。"""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

from config import create_llm


def _build_advisor(
    llm: ChatOpenAI,
    role: str,
    prompt_text: str,
) -> Runnable[dict, str]:
    """使用共享模型和输出解析器构建单个顾问 Chain。"""
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", role),
            ("human", prompt_text),
        ]
    )
    return prompt | llm | StrOutputParser()


def build_advisors() -> dict[str, Runnable[dict, str]]:
    """构建目的地、预算、交通、美食、文化 5 个顾问 Chain。"""
    llm = create_llm()
    advisors = {
        "destination": _build_advisor(
            llm,
            "你是一位资深目的地顾问，擅长景点、住宿、路线和当地玩法。",
            "用户旅行信息：目的地：{destination}，天数：{days}，预算：{budget}。\n"
            "请给出目的地推荐、必去景点、建议住宿区域和每日行程建议，控制在 250 字内。",
        ),
        "budget": _build_advisor(
            llm,
            "你是一位严谨的预算规划师，擅长把总预算拆分到旅行各项支出。",
            "用户旅行信息：目的地：{destination}，天数：{days}，预算：{budget}。\n"
            "请给出住宿、交通、餐饮、门票和其他支出的预算分配，控制在 200 字内。",
        ),
        "transportation": _build_advisor(
            llm,
            "你是一位交通顾问，擅长城市内外的交通方式和通勤安排。",
            "用户旅行信息：目的地：{destination}，天数：{days}，预算：{budget}。\n"
            "请给出到达目的地、城市内通勤和每日交通安排建议，控制在 200 字内。",
        ),
        "food": _build_advisor(
            llm,
            "你是一位当地美食顾问，熟悉特色菜、餐厅和餐饮体验。",
            "用户旅行信息：目的地：{destination}，天数：{days}，预算：{budget}。\n"
            "请推荐当地必吃美食、推荐餐厅和每日用餐建议，控制在 200 字内。",
        ),
        "culture": _build_advisor(
            llm,
            "你是一位文化顾问，擅长历史、民俗、演出和旅行文化注意事项。",
            "用户旅行信息：目的地：{destination}，天数：{days}，预算：{budget}。\n"
            "请介绍当地文化亮点、特色活动、注意事项和礼仪，控制在 200 字内。",
        ),
    }
    return advisors
