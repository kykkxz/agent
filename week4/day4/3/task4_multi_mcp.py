"""多 MCP Server 数据聚合助手。"""

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
    """同时连接职位、公司和薪资三个 MCP 服务并启动对话。"""
    server_config = {
        "jobs": {
            "transport": "stdio",
            "command": sys.executable,
            "args": [str(BASE_DIR / "server_jobs.py")],
        },
        "company": {
            "transport": "stdio",
            "command": sys.executable,
            "args": [str(BASE_DIR / "server_company.py")],
        },
        "salary": {
            "transport": "stdio",
            "command": sys.executable,
            "args": [str(BASE_DIR / "server_salary.py")],
        },
    }

    mcp_client = MultiServerMCPClient(server_config) #type: ignore[reportArgumentType]
    tools = await mcp_client.get_tools()

    llm = ChatOpenAI(
        model=os.getenv("MODEL_NAME"),#type: ignore[reportArgumentType]
        api_key=os.getenv("API_KEY"),#type: ignore[reportArgumentType]
        base_url=os.getenv("BASE_URL"),
        temperature=0.3,
    )

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=(
            "你是一个职业发展和招聘咨询助手。你可以同时使用职位查询、公司信息和"
            "薪资计算三个 MCP 服务。面对复合问题时，分别调用所需工具，综合多个工具"
            "的结果后用中文清晰回答。"
        ),
    )

    print("多 MCP Server 数据聚合助手已启动，输入 exit 退出。")
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
