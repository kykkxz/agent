# 0807工作目标

- 回顾：agent，function calling，mcp，transport参数选用（stdio/sse--streamable http），多agent搭建（商业项目）-路由agent，mulit-agent并行任务

- langgraph-实战案例

- langchain vs langgraph  vs dify/coze 区别和应用
  
  
  
  

## 模块0：mulit-agent并行任务

   基于MCP协议：大模型当作tool，通过MCP协议进行调用，给到响应的参数

  多agent方案：多个顾问作为独立的agent节点，由路由主管做节点调度，支持并行，条件跳转等



架构上的问题：

-工具是没有办法保存上下文的

-asynic 锁管理

-分发决策比较难精细化，路由agent智能输出工具名称，参数，难以进行结构化存储



上下文通信缺陷：

上下文膨胀:每次调用mcp顾问工具，主管都必须把用户的原始提问，其他顾问产出的内容和历史对话全部塞进工具请求参数。各种参数不断叠加，prompt上下文长度爆炸，token小号飙升



整合起来成本很高：

mcp下的工具调用的输出结果会有冲突，一旦业务新增别的节点，路由判断逻辑，工具参数都需要改动；多agent模式下，只需要修改路由agent的prompt。



### 什么时候 MCP 工具模式适合该项目？

仅适合**轻量单次查询**，例如用户只单独询问美食，单次调用美食顾问工具；

只要涉及多 Agent 协同、行程联动、多轮修正、子 Agent 通信，MCP 工具调用方案弊端会被无限放大，优先选用 LangGraph 多 Chain‑Agent 架构。



# 模块1：langchain->langgraph

场景：it公司智能系统，针对用户提问，将问题分发给响应的agent进行处理



任务或者问题，数据库专家，必须再后端完成的基础上，确定相关内容

“做一个电商下单、支付、订单取消的后端业务”



## 一、Langchain的痛点

Langchain是普通链式结构，对于复杂业务流程难以实现，需要写很多判断分支和组合，十分冗余，且容易出错，不好排查问题

- 分支判断

- 并行执行

- 状态持久流转

- 循环任务：自我反思，工具调用，多次修正答案（没有回退机制）

- 等待机制

Langgraph：图结构，基于状态机的LLM Agent编排框架，继承Langchain，用图结构来管理节点、状态、路由分支、并发、循环



## 二、Langgraph五大核心概念

### 1.状态机state

整个流程图的全局的类，所有节点都可以读取和修改这个状态机里的数据（python使用TpyeDict来定义字段）

### 2. 节点node

每一个节点函数会接收当前state，返回一个需要更新的字典，自动合并到状态机

### 3.边 edge

add_edge(A,B)来创建两个节点之间的关联

- START:流程图的入口

- END：流程图的出口

### 4.条件边conditional-edge

动态路线，根据函数的返回值决定下一步要去到哪一个节点

**返回单一字符串-->串行跳转；返回字符串列表-->开启多节点并发执行**

### 5.Workflow工作流

StateGraph实例，添加节点，配置路线之后compile成可运行对象，调用.invoke（初始状态）启动智能体



第一步：定义状态
class AgentState(TypedDict):
    question:str
    next_nodes: List[str]
    frontend_answer: str   # 专门存放前端的回答
    backend_answer: str    # 专门存放后端的回答
    final_answer: str      # 最终整理好的回答



第二步：定义各个员工节点 (Nodes)

def supervisor_agent(state: AgentState):



第三步：路由函数

def route_to_departments(state: AgentState):
    return state["next_nodes"]



第四步：组装带并发的图 (LangGraph)

def build_parallel_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("supervisor", supervisor_agent)
    workflow.add_node("frontend", frontend_agent)
    workflow.add_node("backend", backend_agent)
    workflow.add_node("unknown", unknown_agent)
    workflow.add_node("summarizer", summarizer_agent)

    workflow.add_edge(START, "supervisor")

    workflow.add_conditional_edges(
        "supervisor",
        route_to_departments,
        ["frontend", "backend", "unknown"]
    )

    workflow.add_edge("frontend", "summarizer")
    workflow.add_edge("backend", "summarizer")

    workflow.add_edge("summarizer", END)
    workflow.add_edge("unknown", END)

    return workflow.compile()



第五步：运行测试

if __name__ == "__main__":
    app = build_parallel_graph()

    initial_state = {"question": q, "next_nodes": [], "frontend_answer": "", "backend_answer": "", "final_answer": ""}

    result = app.invoke(initial_state)



```python
import os
from typing import TypedDict, List
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END
import json

# 1. 加载环境变量
load_dotenv()
api_key = os.getenv("API_KEY")
base_url = os.getenv("BASE_URL")
model_name = os.getenv("MODEL_NAME")

# 2. 初始化大模型
llm = ChatOpenAI(
    model=model_name,
    api_key=api_key,
    base_url=base_url,
    temperature=0.7
)

#主管节点（低耗模型）
supervisor_llm = ChatOpenAI(
    model=model_name,
    api_key=api_key,
    base_url=base_url,
    temperature=0.1
)

#第一步：定义状态
class AgentState(TypedDict):
    question:str
    next_nodes: List[str]
    frontend_answer: str   # 专门存放前端的回答
    backend_answer: str    # 专门存放后端的回答
    final_answer: str      # 最终整理好的回答

# 第二步：定义各个员工节点 (Nodes)

def supervisor_agent(state: AgentState):
    print("👔 [主管] 正在分析问题类型...")
    prompt = ChatPromptTemplate.from_template(
        "你是一个IT公司的项目主管。请分析客户的问题：【{question}】。\n"
        "如果属于前端，输出 frontend；属于后端，输出 backend；如果都有，输出 both；如果不属于技术，输出 unknown。"
        "你的输出只能是上面四个词之一："
    )
    response = (prompt | supervisor_llm).invoke({"question": state["question"]})
    decision = response.content.strip().lower()

    # 根据大模型的决定，将任务拆分成列表
    if decision == "both":
        next_nodes = ["frontend", "backend"]
        print("   👉 决定：这个问题太复杂，【前端】和【后端】给我同时处理！")
    elif decision == "frontend":
        next_nodes = ["frontend"]
        print("   👉 决定：交给【前端】处理。")
    elif decision == "backend":
        next_nodes = ["backend"]
        print("   👉 决定：交给【后端】处理。")
    else:
        next_nodes = ["unknown"]
        print("   👉 决定：非技术问题，交给【客服】。")    

    return {"next_nodes": next_nodes}

def frontend_agent(state: AgentState):
    print("🎨 [前端部门] 收到！正在并发处理前端问题...")
    prompt = ChatPromptTemplate.from_template("你是一个前端专家，请用不超过50个字解答：{question}")
    response = (prompt | llm).invoke({"question": state["question"]})
    return {"frontend_answer": response.content}

def backend_agent(state: AgentState):
    print("⚙️  [后端部门] 收到！正在并发处理后端问题...")
    prompt = ChatPromptTemplate.from_template("你是一个后端专家，请用不超过50个字解答：{question}")
    response = (prompt | llm).invoke({"question": state["question"]})
    return {"backend_answer": response.content}

def unknown_agent(state: AgentState):
    print("🤷‍♂️ [客服部门] 收到，正在回复...")
    return {"final_answer": "您好，这超出了我们的服务范围。"}

def summarizer_agent(state: AgentState):
    print("📝 [合并专员] 收集到了各部门的报告，正在整理最终回复...")

    parts = []
    if state.get("frontend_answer"):
        parts.append(f"【前端视角】 {state['frontend_answer']}")
    if state.get("backend_answer"):
        parts.append(f"【后端视角】 {state['backend_answer']}")

    final_answer = "\n".join(parts)
    return {"final_answer": final_answer}

# 第三步：路由函数
def route_to_departments(state: AgentState):
    return state["next_nodes"]

# 第四步：组装带并发的图 (LangGraph)
def build_parallel_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("supervisor", supervisor_agent)
    workflow.add_node("frontend", frontend_agent)
    workflow.add_node("backend", backend_agent)
    workflow.add_node("unknown", unknown_agent)
    workflow.add_node("summarizer", summarizer_agent)

    workflow.add_edge(START, "supervisor")

    workflow.add_conditional_edges(
        "supervisor",
        route_to_departments,
        ["frontend", "backend", "unknown"]
    )

    workflow.add_edge("frontend", "summarizer")
    workflow.add_edge("backend", "summarizer")

    workflow.add_edge("summarizer", END)
    workflow.add_edge("unknown", END)

    return workflow.compile()

if __name__ == "__main__":
    app = build_parallel_graph()
    print("🚀 启动 LangGraph 并发与状态流转测试...\n")

    test_questions = [
        "Vue3 和 Python 分别适合用来做什么？",
    ]

    for q in test_questions:
        print("="*50)
        print(f"👤 客户提问: {q}\n")

        initial_state = {"question": q, "next_nodes": [], "frontend_answer": "", "backend_answer": "", "final_answer": ""}
        result = app.invoke(initial_state)

        print(f"\n🎉 最终回复: \n{result['final_answer']}")
        print("\n🧰 让我们打开公文包(State)看看里面的痕迹：")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("="*50)    
```



场景提问：

it系统开发公司

topic--某种网站产品/线上系统

营销部/ui设计部/前端/后端/测试/项目经理



topic-营销部- 营销方案

topic+营销方案-ui-ui界面

topic +ui界面-前端-前端代码

topic +ui界面-后端-后端代码

前端代码+后端代码-测试部

所有部门的输出-项目经理-END





![fea3b516-ab5c-4376-aa6a-c4bf3f118e9a](file:///C:/Users/qiuxingyu/OneDrive/Pictures/Typedown/fea3b516-ab5c-4376-aa6a-c4bf3f118e9a.png)



任务：基于这个流程图构建agent

需要完成所有节点的流通逻辑，代码可运行可展示，每个节点输出可以少于30字。

扩展任务：

1.合规审核部：营销部写完slogan，不能出现“最”，“第一”这种字眼，违反广告，一旦出现，就需要打回重做

2.循环重试机制：营销部接到打回意见，需要根据意见修改，但允许的次数有限（3次）

3.风控兜底部：当营销部试了3次不能通过，强制性返回一个符合要求的数据，给出一个“绝对安全”的营销兜底方案，强行到UI部门。



![80d4af6e30e9c873123b5ebca8b34d6f](file:///C:/Users/qiuxingyu/OneDrive/%E6%96%87%E4%BB%B6/Tencent%20Files/995717051/nt_qq/nt_data/Pic/2026-08/Ori/80d4af6e30e9c873123b5ebca8b34d6f.png)

【验收标准】

兜底方案改为：失败一次即兜底。

retry参数改回3次，验证退回机制。





# 模块2：LangChain vs LangGraph vs Coze/Dify

### 1.三者核心定位：

- coze/dify:可视化拖拽的低代码平台，快速演示demo

- Langchain：大模型组件库，适配简单线性业务，快速验证想法（相对常用）

- Langgraph：可编程状态工作引擎，支撑复杂逻辑和生产级上线

### 2. 核心能力差异

| 对比维度  | Coze/Dify    | LangChain     | LangGraph      |
| ----- | ------------ | ------------- | -------------- |
| 开发形式  | 低代码          | python        | python         |
| 流程形态  | 固定线性流程       | 单向链式结构        | 支持循环，分支，并行流转   |
| 状态管控  | 平台托管         | 弱状态           | 全局状态管理         |
| 循环重试  | 不支持失败重试，闭环循环 | 黑盒循环，死循环      | 自主控制循环次数       |
| 多智能体  | 简单分流，不能协作    | 简易多agent，难以扩展 | 智能体之间的分工协作，通信  |
| 人工接入  | 不支持          | 难以实现          | 可设置断点，人工审核后继续跑 |
| 自定义程度 | 低            | 中等，基本定制       | 极高             |
| 适用阶段  | 汇报、poc验证     | 小型简单业务，快速原型   | 复杂项目，正式线上项目    |

### 3.关键点说明

- coze/dify：工作流搭建应用

- react机制：Langchain内置思考嗲用机制，异常场景难以处理；Langgraph将思考，工具调用，判断步骤都拆分成独立节点，自主编写路由规则，精准把握每一次推理

- 多agent协作：Langchain可实现角色分流调用，但无法退回重写等，Langgraph依靠全局状态传递信息


