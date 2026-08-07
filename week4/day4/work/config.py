"""系统配置：加载环境变量并创建共享语言模型。"""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def create_llm() -> ChatOpenAI:
    """创建使用 .env 配置的 ChatOpenAI 实例。"""
    return ChatOpenAI(
        model=os.getenv("MODEL_NAME"), #type: ignore[reportArgumentType]
        api_key=os.getenv("API_KEY"),#type: ignore[reportArgumentType]
        base_url=os.getenv("BASE_URL"),
        temperature=0.4,
    )
