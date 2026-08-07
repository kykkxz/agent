import json
import os

import requests
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI


load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

API_TOKEN = os.getenv("EXTERNAL_API_TOKEN")
HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}


@tool
def get_dujitang() -> str:
    """生成一句毒鸡汤。"""
    print("[工具调用] get_dujitang()")
    response = requests.get(
        "https://v2.xxapi.cn/api/dujitang",
        headers=HEADERS,
    )
    return json.dumps(response.json(), ensure_ascii=False)


@tool
def get_phone_fortune(phone: str) -> str:
    """查询指定手机号的手机运势。"""
    print(f"[工具调用] get_phone_fortune(phone={phone})")
    response = requests.get(
        "https://v2.xxapi.cn/api/phonejixiong",
        params={"phone": phone},
        headers=HEADERS,
    )
    return json.dumps(response.json(), ensure_ascii=False)


@tool
def get_ip(ip: str = "122.228.216.223") -> str:
    """查询指定 IP 地址的信息。"""
    print(f"[工具调用] get_ip(ip={ip})")
    response = requests.get(
        "https://v2.xxapi.cn/api/ip",
        params={"ip": ip},
        headers=HEADERS,
    )
    return json.dumps(response.json(), ensure_ascii=False)


@tool
def calculate(expression: str) -> str:
    """计算只包含数字和加号的加法表达式，例如 1+2+3。"""
    print(f"[工具调用] calculate(expression={expression})")
    numbers = [float(number.strip()) for number in expression.split("+")]
    result = sum(numbers)
    return str(int(result) if result.is_integer() else result)


llm = ChatOpenAI(
    model=os.getenv("MODEL_NAME"), #type: ignore[reportArgumentType]
    api_key=os.getenv("API_KEY"),#type: ignore[reportArgumentType]
    base_url=os.getenv("BASE_URL"),
    temperature=0.3,
)

tools = [get_dujitang, get_phone_fortune, get_ip, calculate]
agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=(
        "你是一个多功能生活助手。请根据用户问题选择合适的工具，"
        "需要实时信息时必须调用工具，并用中文简洁回答。"
        "查询手机运势时必须先获得用户提供的手机号；如果用户没有提供，"
        "先询问手机号，再调用 get_phone_fortune。"
    ),
)


if __name__ == "__main__":
    print("多功能生活助手已启动，输入 exit 退出。")
    messages = []

    while True:
        question = input("你：").strip()
        if question.lower() == "exit":
            break

        messages.append(("user", question))
        result = agent.invoke({"messages": messages})
        messages = result["messages"]
        print(f"助手：{messages[-1].content}")
