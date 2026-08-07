"""互联网工具 MCP 聚合助手。"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")


async def main() -> None:
    """连接互联网工具 MCP 服务并启动多轮对话。"""
    mcp_client = MultiServerMCPClient(
        {
            "internet": {
                "transport": "stdio",
                "command": sys.executable,
                "args": [str(BASE_DIR / "server_internet.py")],
            }
        }
    )
    tools = await mcp_client.get_tools()

    llm = ChatOpenAI(
        model=os.getenv("MODEL_NAME"),
        api_key=os.getenv("API_KEY"),
        base_url=os.getenv("BASE_URL"),
        temperature=0.3,
    )

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=(
            "你是一个万能互联网查询助手。根据用户问题选择合适的互联网工具，"
            "需要多个来源时分别调用工具并综合结果。IP 查询、维基百科、时区、"
            "域名信息和毒鸡汤请求都必须优先使用对应工具，并用中文回答。"
        ),
    )

    print("互联网工具 MCP 聚合助手已启动，输入 exit 退出。")
    messages = []

    while True:
        question = input("用户：").strip()
        if question.lower() == "exit":
            break

        messages.append(("user", question))
        result = await agent.ainvoke({"messages": messages})
        messages = result["messages"]
        print(f"助手：{messages[-1].content}")


if __name__ == "__main__":
    asyncio.run(main())
