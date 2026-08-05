import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_openai import ChatOpenAI


load_dotenv(Path(__file__).with_name(".env"))

MODEL_ID: str = os.getenv("MODEL_ID") or "gpt-4o-mini"

llm = ChatOpenAI(
    model=MODEL_ID,
    api_key=os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL") or os.getenv("ANTHROPIC_BASE_URL"),
)


def _message_content(response) -> str:
    """提取 LangChain 消息中的文本内容。"""
    content = response.content
    return content.strip() if isinstance(content, str) else str(content).strip()


def call_llm(title, descs, feature):
    """使用 PromptTemplate 生成推广文案。"""
    prompt_template = PromptTemplate(
        input_variables=["title", "descs", "feature"],
        template="""你是一名专业文案编辑，请为下面的主题写一段推广文案。
要求：语气轻松活泼，内容突出产品特点，字数控制在 100 字以内。

主题：{title}
描述：{descs}
特点：{feature}
""",
    )
    prompt = prompt_template.format(
        title=title,
        descs=descs,
        feature=feature,
    )
    print(prompt)

    response = llm.invoke(prompt)
    return _message_content(response)


def call_llm2(title, descs, feature):
    """使用 ChatPromptTemplate 生成 slogan。"""
    question = f"""请根据以下信息生成一句简洁、有吸引力的 slogan：
主题：{title}
描述：{descs}
特点：{feature}"""

    chat_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是一个资深的文案编辑，拥有 10 年以上从业经验。",
            ),
            ("human", "{question}"),
            (
                "ai",
                "人工智能（AI）是能够模拟人类学习、理解和解决问题能力的技术。",
            ),
            ("human", "现在请根据前面的信息生成一句 slogan。"),
        ]
    )
    messages = chat_prompt.format_messages(question=question)

    response = llm.invoke(messages)
    return _message_content(response)

if __name__ == "__main__":
    print(call_llm("生活", "早起", "轻松"))
