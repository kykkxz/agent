# 0805工作目标

- langchain的基本核心组件：modelI/O，chains，agent

- function calling

- MCP协议：实战

- 实战任务
  
  

# 一、认识Langchain

## 1.介绍

大模型：具有大量参数和复杂结构的神经网络模型，基于海量数据预训练而来的生成式模型，能够完成各种复杂的任务，处理各种nlp，cv领域的任务

```
我没办法直接帮你完成机票预订操作，预订机票需要实名信息、个人支付操作。
你可以自行在携程、去哪儿、各大航空公司官方 APP 查询中秋节前往青岛的航班、对比票价下单购票。
```

智能体：大模型+工具+上下文管理。大模型本身只具备思考能力，不具备行动能力。在大模型的基础上赋予他实际行为能力。

json结果-->接口，操作。{}数据，api接口调用，帮我完成认证和登录和订票。

Langchain:把以上操作对应的底层代码进行封装的第三方库，2022年哈佛研发的一个开源框架，主要用于开发由大模型驱动的应用程序，比如：搭建智能体，问答系统，对话机器人，文档搜索等。

Langchain发布比chatgpt还早一个月。

## 2. 版本问题

目前使用的话，建议都用1.0版本，这个版本是里程碑式的更新，比较稳定的状态，简化0.x开发流程，统一了api标准。去除了之前杂乱的库。

## 3.相关框架

目前比较火的有哪些可以做大模型开发的框架

| 框架                              | 描述                                              |
| ------------------------------- | ----------------------------------------------- |
| LangChain（python）               | 出现最早，最成熟，适合复杂的任务分解和单Agent应用                     |
| llamaindex(python)              | 专注于高效的索引和检索，适合RAG（增强检索生成）场景                     |
| LangChain4J（Java）               | LangChain推出的Java版本，功能略少于LangChain,但是核心功能都有      |
| SpringAI/SpringAI Alibaba（Java） | Spring和Alibaba推出的针对大模型的操作工具，主要针对接口进行了一些封装，功能待完善 |
| SemanticKernel(C#)              | 微软推出的，对于C#的开发者这个是最好用的                           |

### 4.为什么要用langchain？

- 简化开发难度：更高效，更加简单，相对简洁容易上手

- 开发人员：更多关注业务逻辑本身，需要产品经理思维（思考这种场景问题），不需要花费大量的精力去处理底层的技术细节

- 学习成本更低：不同的模型api会有所不同，调用方式也不同，切换模型的时候成本高，langchain进行了统一规范，有更好的移植性。

- 现成的链式组装：提供一些线性的链式组装，可以完成特定的高级任务，让本身复杂的逻辑变得更加结构化，易组合，易拓展

- 具体的功能：LLM应用构建的全套工具包，prompt构建，LLM接入，记忆管理，工具调用，rag，agent开发。
  
  

**LangChain的使用场景**

| 场景          | 技术点                         |
| ----------- | --------------------------- |
| 文档问答助手（RAG） | Prompt/Embedding/Retrieval  |
| 智能日程规划助手    | Agent+Tool+Memory           |
| LLM+数据库问答   | sqldatabasetoolkit+Agent    |
| 多模型路由对话助手   | routerchain+多LLM            |
| 互联网智能客服     | ConversationChain+RAG+Agent |
| 企业知识库助手     | VectorDB+LLM                |

电商购物平台设计的场景和技术点：？

教辅类agent开发：海量数据？



## 二、Agent和Rag

## 1.Agent:

agent是一个完整的身体，带有聪明的大脑

Agent=LLM+TOOL+MEMORY+PLANNING

观察环境->思考决策->采取行动->获得反馈->再思考

![0f3d8d03-1547-449b-aad4-42afd2be1d6a](file:///C:/Users/qiuxingyu/OneDrive/Pictures/Typedown/0f3d8d03-1547-449b-aad4-42afd2be1d6a.png)

## 2.RAG:检索增强生成

### 2.1 RAG能解决什么问题？

- 幻觉

- 知识滞后和训练成本高

#### 2.2 RAG的基本工作流程

- 准备知识库：pdf文档

- 检索相关文本块

- 生成回答

## 3.Agent vs RAG vs SFT(监督微调) vs Prompt Engineering

面对一个新需求，你要如何开始，如何选择技术方案？

①直接通过few-shot或者CoT，改进模型的回答（最简单最无成本的解决方案）

②其他方式

![48b14e4a-eef4-402b-882c-1eff8860fb56](file:///C:/Users/qiuxingyu/OneDrive/Pictures/Typedown/48b14e4a-eef4-402b-882c-1eff8860fb56.png)

③微调的作用，不能通过rag直接检索外部知识解决，需要重构LLM的知识体系：垂类大模型（针对某种领域的语料对通用大模型做微调或者继续预训练，比如医疗，法律，金融）、特定任务（特定的医疗方面的实体和关系，用以构建知识图谱）、某种偏好（语言语气人格偏好，游戏公司--npc具备人物独有的人设和回答）---实际业务中谨慎，强依赖于领域知识

参考资料：

[传承与创新：云南白药携手华为共谋医药数智化转型“妙方” - 华为](https://e.huawei.com/cn/case-studies/industries/manufacturing/202501-group-cloud-yunnanbaiyao)

https://zhuanlan.zhihu.com/p/1948792814621161196



## 三、Langchain的核心组件

核心组件：Model I/O 、Chains 、RAG、Agents

### Model I/O

![img](/D:\网讯\讲师内容\提升班课_0407起/%E7%BA%BF%E4%B8%8B%E8%AE%B2%E4%B9%89.assets/b8d8bb5ead3a1d3f0bd53c6968814539.png)

- format:通过模版管理大模型的输入。将原始数据格式化为模型可以处理的形式，插入到模版中，然后送给模型进行处理

- predict:调用llm（instruct/chat）接口，进行预测或者生成回答

- parse：规范化大模型的输出，比如大模型的输出格式规定为json格式
  
  

### Chains

链条：将多个组件组合成一个完成的流程，方便链式调用

组件：水管本身

链接:"|“  数据的链条式处理

chain = prompt | llm | parser (一个链条也可以成为一个单独的组件)

统一的组件调用方法.invoke()



### Retrieval：RAG的组件

![img](/D:\网讯\讲师内容\提升班课_0407起/%E7%BA%BF%E4%B8%8B%E8%AE%B2%E4%B9%89.assets/f4d668418d4f1360bc62ff3f9e27e562.png)

Source： 多种类型的数据源：文本、图片、音频、视频、代码、文档等 ==> 多模态的rag

load： 将多源异构数据统一加载为文档对象

transform：对文档进行转换和处理，比如将文本切分为小块

Embed： 将文本编码为向量

Store： 将向量化后的数据存储起来

retrieve： 从文本库中检索相关的文本段落



### Agents：

![img](/D:\网讯\讲师内容\提升班课_0407起/%E7%BA%BF%E4%B8%8B%E8%AE%B2%E4%B9%89.assets/708fd20300169af702a911bc54b20a8d.png)

预计最近一周成都有雨的那几天现有xx班次的火车票还剩余多少张？---调用多个tool



## 四、Langchain的实战

### 1.安装环境：严格按照版本安装，langchain版本之间代码差异很大，ai难以调试

```python
langchain==1.2.15
langchain-core==1.3.1
langchain-openai==1.2.0
langgraph==1.1.9
python-dotenv==1.2.2
pydantic==2.13.3
mcp==1.27.0
langchain-mcp-adapters==0.2.2
```

```
#可选择性安装
# 模型和嵌入支持 按需安装
pip install langchain-openai
pip install langchain-ollama
pip install langchain-huggingface

#  向量库 按需安装
pip install chroma 
pip install faiss-cpu

# 辅助工具
 pip install tiktoken # openai token计数 如果用的是ollama 可以暂时不用
```

### 2. Langchain详解

#### 2.1 基础环境配置

创建.env文件，填入你的大模型API-key（如硅基流动等）

```python
API_KEY=sk-xxxxxxxxxxxxxx
BASE_URL=https://api.siliconflow.cn/v1
MODEL_NAME=qwen-flash
```

### 2.2 编写第一个大模型调用

llm = ChatOpenAI()

llm.invoke()

response.content

for chunk in llm.stream(query):

     print(chunk.content,end="", flush=True)

    

```python
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("API_KEY")
base_url = os.getenv("BASE_URL")
model_name = os.getenv("MODEL_NAME")

llm = ChatOpenAI(
    model=model_name,
    api_key=api_key,
    base_url=base_url
)

response = llm.invoke("你好")
print(response.content)

for chunk in llm.stream("怎么打好王者荣耀"):
    print(chunk.content,end="", flush=True)
```

### 2.3  PromptTemplate vs ChatPromptTemplate

总结：PromptTemplate是“纯字符串模版”，将原本的文本补全给原生模型（Intstruct）使用；ChatPromptTemplate是“带角色的消息列表模版”，给chat模型（GPT3.5/Claude等)，天然支持多轮对话

![2c31e840-18bd-43e1-be31-2f36eae39509](file:///C:/Users/qiuxingyu/OneDrive/Pictures/Typedown/2c31e840-18bd-43e1-be31-2f36eae39509.png)

instruct类型的模型，只能接收PromptTemplate模版的输入，ChatPromptTemplate输入会报错

![03ff083e-d330-4f8b-8a80-8dc2abc1ca35](file:///C:/Users/qiuxingyu/OneDrive/Pictures/Typedown/03ff083e-d330-4f8b-8a80-8dc2abc1ca35.png)

chat类型模型（平时调用），语法上是可以兼容两种PromptTemplate 和 ChatPromptTemplate，但是为了符合多轮对话管理的特性，更推荐配套使用ChatPromptTemplate。

### 1.本质与数据结构不同

- PromptTemplate--instuct/chat模型
  继承：StringPromptTemplate
  输出：单一字符串（不会有角色）
  内部：一段字符串，或者带变量的文本

```python
from langchain_core.prompts import PromptTemplate

prompt = PromptTemplate.from_template("讲一个关于{topic}的笑话")

print(prompt.invoke({"topic":"猫"}))
```

- ChatPromptTemplate
  强角色区分：System，human，ai
  
  ```
  from langchain_core.prompts import ChatPromptTemplate
  chat_prompt = ChatPromptTemplate.from_messages([
      ("system", "你是一个幽默的助手"),
      ("human", "讲一个关于{topic}的笑话")
  ])
  print(chat_prompt.invoke({"topic": "猫"}))
  # 输出：
  # ChatPromptValue(messages=[
  #   SystemMessage(content='你是一个幽默的助手'),
  #   HumanMessage(content='讲一个关于猫的笑话')
  # ])
  ```

#### 课堂任务

任务背景：

假设你是一家新媒体公司的内容策划，每天需要为不同产品/话题写推广文案。现在你想用大模型来帮你写，但每次手动拼提示词太麻烦了，你决定用 LangChain 的 \*\*提示词模板\*\* 来自动化这个流程。

任务需求

 需求 1：用 `PromptTemplate` 写一个文案生成函数

1\. 定义一个函数 `call_llm(title, descs, feature)`

2\. 使用 `PromptTemplate` 创建一个纯文本提示词模板，模板中需要包含 3 个变量：`title`（主题）、`descs`（描述）、`feature`（特点）

3\. 提示词内容要体现：你是一个专业文案编辑，要求语气轻松活泼，字数控制在 100 字以内

4\. 初始化 `ChatOpenAI` 模型，使用 `.env` 文件里的配置

5\. 将三个变量填入模板，调用模型生成文案

6\. 把最终拼好的提示词打印出来，方便检查

7\. 返回模型生成的文案内容

需求 2：用 `ChatPromptTemplate` 写一个带角色的文案生成函数

1\. 定义一个函数 `call_llm2(title, descs, feature)`

2\. 使用 `ChatPromptTemplate.from_messages` 创建消息模板，要求：

- `system` 角色：设定身份（比如"你是一个资深的文案编辑，拥有 10 年以上从业经验"）

- `human` 角色：传入拼接好的需求信息

- `ai` 角色：给一个参考样例（比如先解释一下 AI 是什么）

- 再追加一个 `human` 角色：让模型生成一句 slogan

3\. 将 `title`、`descs`、`feature` 拼成一段完整的 question 字符串

4\. 调用模型生成内容，返回文案

#### 2.使用的模型和场景

PromptTemplate 适合：

- 传统文本补全模型：

- 单轮/简单任务：翻译/摘要/简单问答

- 不需要区分系统设定和用户输入的场景

Chat PromptTemplate适合：

- 现代对话模型

- 多轮对话/聊天机器人/Agent

- 需要系统人设/用户提问/历史对话的复杂上下文

```
from langchain_openai import OpenAI
llm = OpenAI()
prompt = PromptTemplate.from_template("总结：{text}")
chain = prompt | llm
```

```
from langchain_openai import ChatOpenAI
chat_model = ChatOpenAI()
chat_prompt = ChatPromptTemplate.from_messages([...])
chain = chat_prompt | chat_model
```

#### 3.核心区别速览表

| 特性   | PromptTemplate    | ChatPromptTemplate  |
| ---- | ----------------- | ------------------- |
| 结构   | 纯字符串              | 消息列表（带 role）[]      |
| 角色   | 无                 | system / human / ai |
| 输出类型 | StringPromptValue | ChatPromptValue     |
| 适配模型 | LLM（文本补全）         | ChatModel（对话）       |
| 多轮对话 | 不支持               | 原生支持（可插历史消息）        |
| 典型场景 | 摘要、翻译、简单问答        | 聊天机器人、Agent、复杂指令    |

#### 4.两种类型的模型

#### 4.1Instruct指令模型

只为单轮任务执行设计，无对话交互能力，只识别纯文本指令，不支持任何角色和工具能力

* ❌ 不识别 system/human 角色消息格式

* ❌ 不支持多轮上下文、人设

* ❌ 不支持 Function Calling、工具调用

* ❌ 不支持 with\_structured\_output 高阶能力

```python
from langchain_openai import OpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Instruct模型初始化（阿里云通义千问）
llm = OpenAI(
    api_key="你的阿里云API_KEY",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    model="qwen2-72b-instruct",
    temperature=0.1
)

# 只能使用 PromptTemplate 纯字符串模板
prompt = PromptTemplate.from_template("根据资料回答问题：{context}\n问题：{question}")

# 构建链路
chain = prompt | llm | StrOutputParser()

# 调用执行
res = chain.invoke({"context": "LangChain是大模型开发框架", "question": "LangChain的作用是什么？"})
print(res)
```

#### 4.2 Chat对话模型

专为人机交互/多轮对话。兼容文本指令+角色对话，支持人设/记忆/闲聊/工具调用/agent开发。

* ✅ 兼容 PromptTemplate 纯文本模板（不推荐生产）

* ✅ 完美适配 ChatPromptTemplate 角色模板（官方推荐）

* ✅ 支持所有解析器、工具调用、结构化输出
  
  
  
  

### 2.4 三种解析方式

prompttemplate/chatprompttemplate-- LLM--StrOutputParser/JsonOutputParser/with\_structured\_output

#### 1)StrOutputParser:简单的文本解析

### 2）JsonOutputParser/with\_structured\_output

将模型输出的非结构化文本，转换成结构化数据（如Json，字典)，避免手动提取，切分数据，减少错误

**方式一**：JsonOutputParser

- 将模型输出标准的json字符串，支持通过key取值，用于结构化数据的提取

- Instruct（需Prompt强制输出Json）和Chat模型都可以用

- 先定义Pydantic结构，然后通过json_parser.get_format_instructions()告诉模型，你需要按这个json格式返回

- 特点：比较清点，控制感强，模型足够听话

```
class People(BaseModel):
    name: str = Field(description="姓名")
    age: int = Field(description="年龄")
    sex: str = Field(description="性别")
    address: str = Field(description="地址")

def call_llm():
    llm = ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url
    )
    json_parser = JsonOutputParser(pydantic_object=People)    
    messages = [
    SystemMessage(content=json_parser.get_format_instructions()),  # 生成响应 JSON 的系统提示词
    HumanMessage(content="给我生成1个人的数据")
    ]
    print("============================")
    print(messages)
    # 调用模型
    response = llm.invoke(messages)
    resp = json_parser.invoke(response)
    print("000000000000000000000000000000")
    print(resp)
```

**方式二**：with\_structured\_output

- Langchain的高阶封装，不需要去手动配置Prompt格式，模型可以直接输出结构化对象

- **Instruct模型完全不支持**、✅ Chat模型专属

- 需要直接定义json_schema，容易写错，llm.with_structured_output(...)返回结果，模型返回时会尽量按结构化给你

- 更现代化，在chat模型中更适合正式的项目，更适合后续做agent，tool和结构化抽取

```
def call_llm2():
    llm = ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url
    )
    json_schema = {
        "name": "AnimalList",
        "schema": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "animal": {
                        "type": "string",
                        "description": "动物名称"
                    },
                    "age": {
                        "type": "integer",
                        "description": "动物年龄"
                    }
                },
                "required": ["animal", "age"],
                "additionalProperties": False
            }
        }
    }

    messages = [
        HumanMessage(content="给我生成1种动物的名称以及对应的年龄")
    ] 
    response = llm.with_structured_output(
        schema=json_schema,
        method="json_schema",
        include_raw=True
    ).invoke(messages)       

    print("=============================================")
    print(response["raw"])
    print("000000000000000000000000000000000000000000000000")
    print(response["parsed"])
```

### 2.5 modelI/O三个组件的搭配(背下来)

- 纯文本任务（无结构化，无交互）：Instruct \+ PromptTemplate \+ StrOutputParser

- 纯结构化抽取（后台任务）：Instruct \+ PromptTemplate \+ JsonOutputParser

- 人机对话、多轮RAG：Chat+ChatPromptTemplate+StrOutputParser

- 工具调用、Agent、高精度结构化抽取：Chat+ChatPromptTemplate+with\_structured\_output
  
  

极简背诵口诀

* Instruct认串不认角色，只能用普通模板，无高阶结构化能力

* Chat通吃所有模板和解析器，对话、任务、工具全能适配

* 普通文本用Str、手动JSON用Json、工具结构化用structured

### 2.6 Chains 链条组件

### 1）概念：

将Model I/O组件或其他工具，按固定的顺序串联起来的流水线，流程写死，步骤也是固定，无自主思考能力，只能按预设逻辑执行

#### 2) 核心依赖：Runnable \+ LCEL 管道

- Runnable：langchain中所有可调用的组件的一个统一接口，，无论是prompt，llm，parser还是chains，agent都是runnable

- 统一调用方式：invoke()同步调用，stream()流式输出，batch()批量处理，不用去记忆不同组件的调用方式

- LCEL 管道符 \|：用来串联多个Ruannable组件，实现上一个组件的输出就是下个一组件的输入，无需手动传递中间结果，简化代码

```python
llm = ChatOpenAI(
    api_key=api_key,
    base_url=base_url,  # 本地/国内大模型可替换
    model_name=model_name,
    temperature=0.1
)

# ======================
# 2. Prompt 输入层（提示词模板）
# ======================
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一名人工智能课程讲师，回答简洁通俗，不超过50字"),
    ("human", "请解释：{user_question}")
])

# ======================
# 3. Output Parser 输出解析层
# ======================
parser = StrOutputParser()

# ======================
# LCEL 链式拼接：prompt | model | parser
# ======================
chain = prompt | llm | parser

# 执行调用
res = chain.invoke({"user_question": "LangChain Model I/O是什么"})
```


