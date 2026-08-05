import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

load_dotenv(Path(__file__).with_name(".env"))

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL") or os.getenv("ANTHROPIC_BASE_URL"),
)
MODEL_ID: str = os.getenv("MODEL_ID") or "gpt-4o-mini"


def call_llm(title, descs, feature):
    """使用纯文本提示词生成推广文案。"""
    prompt = f"""你是一名专业文案编辑，请为下面的主题写一段推广文案。
    要求：语气轻松活泼，内容突出产品特点，字数控制在 100 字以内。

    主题：{title}
    描述：{descs}
    特点：{feature}
    """
    print(prompt)

    response = client.chat.completions.create(
        model=MODEL_ID,
        messages=[{"role": "user", "content": prompt}],
    )
    return (response.choices[0].message.content or "").strip()


def call_llm2(title, descs, feature):
    """使用带角色消息的提示词生成 slogan。"""
    question = f"""请根据以下信息生成一句简洁、有吸引力的 slogan：
    主题：{title}
    描述：{descs}
    特点：{feature}
    """

    messages: list[ChatCompletionMessageParam] = [
        {
            "role": "system",
            "content": "你是一个资深的文案编辑，拥有 10 年以上从业经验。",
        },
        {"role": "user", "content": question},
        {
            "role": "assistant",
            "content": "人工智能（AI）是能够模拟人类学习、理解和解决问题能力的技术。",
        },
        {"role": "user", "content": "现在请根据前面的信息生成一句 slogan。"},
    ]

    response = client.chat.completions.create(
        model=MODEL_ID,
        messages=messages,
    )
    return (response.choices[0].message.content or "").strip()




