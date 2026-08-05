import os
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from pydantic import BaseModel, Field
from typing import List

load_dotenv()

api_key = os.getenv("API_KEY")
base_url = os.getenv("BASE_URL")
model = os.getenv("MODEL_NAME")

user_info = {
    "name": "张三",
    "job": "Python 开发工程师",
    "skills": "Python, LangChain, FastAPI"
}

# 模型初始化
llm = ChatOpenAI(
        model = model,#type: ignore[reportArgumentType]
        api_key = api_key, #type: ignore[reportArgumentType]
        base_url = base_url,
        temperature = 0.3
        )

# 自我介绍生成

## 创建 ChatPromptTemplate
template1 = ChatPromptTemplate.from_messages([
    ("system", "你是一个专业的人力资源顾问，擅长帮人写简洁有力的自我介绍"),
    ("human", "请根据以下信息，帮我写一段 50 字以内的自我介绍。姓名：{name}，职位：{job}，技能：{skills}")
])

## 使用 LCEL 语法组装链
chain = template1 | llm | StrOutputParser()

## 测试打印
result1 = chain.invoke(user_info)

print("生成的自我介绍:")
print("-" * 50)
print(result1)
print("-" * 50)
print(f"是否是 str 类型: {isinstance(result1, str)}")
print()

# 生成个人 slogan 

## 创建PromptTemplate
template2 = PromptTemplate.from_template(
    "请根据以下信息，生成一句 15 字以内的个人 slogan，要求朗朗上口。姓名：{name}，职位：{job}"
)

## 使用LCEL语法组装链
chain = template2 | llm | StrOutputParser()

## 测试打印
result2 = chain.invoke(user_info)

print("=" * 60)
print("个人 Slogan 生成器")
print("=" * 60)
print(f"\n姓名: {user_info['name']}")
print(f"职位: {user_info['job']}")
print("-" * 40)
print(f"生成的 Slogan: {result2}")
print("=" * 60)
print()

# 生成结构化名片数据

## 定义Card类
class Card(BaseModel):
    name: str = Field(description="姓名")
    job: str = Field(description="职位")
    intro: str = Field(description="自我介绍，50字以内")
    slogan: str = Field(description="个人slogan，15字以内，朗朗上口")
    skills: List[str] = Field(description="技能列表")

## 创建JsonOutputParser
parser = JsonOutputParser(pydantic_object=Card)

## 获取格式指令
format_instructions = parser.get_format_instructions()

## 创建 Prompt Template（包含格式指令）
prompt3 = ChatPromptTemplate.from_messages([
    ("system", "你是一个专业的名片生成助手。请根据用户输入，生成一个完整的个人名片信息。\n\n{format_instructions}"),
    ("human", "请为以下人员生成名片：姓名：{name}，职位：{job}，技能：{skills}")
])

## 构建链
chain = prompt3 | llm | parser

## 测试输出

input_data = {
    "name": user_info["name"],
    "job": user_info["job"],
    "skills": user_info["skills"],
    "format_instructions": format_instructions
}

result3 = chain.invoke(input_data)

print("=" * 70)
print("生成的名片信息")
print("=" * 70)
print(f"姓名: {result3['name']}")
print(f"职位: {result3['job']}")
print(f"自我介绍: {result3['intro']}")
print(f"Slogan: {result3['slogan']}")
print(f"技能: {', '.join(result3['skills'])}")
print("=" * 70)


print(f"============================\nAI 智能名片\n============================\n姓名：张三\n职位：Python 开发工程师\n自我介绍：{result1}\n个人 slogan：{result2}\n技能：Python, LangChain, FastAPI\n============================\n")
