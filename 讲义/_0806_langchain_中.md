# 0806工作目标

- function calling

- mcp

- agent
  
  
  
  

### 2.7 Agent

#### （1）定义：

具备自主思考、步骤规划、工具调用能力的智能系统。基于ModelI/O开发，会chains更高级，不需要预设固定流程，能根据用户需求，自主判断“要不要调用工具”，”调用哪个工具“，”按什么顺序调用工具“，”工具调用失败如何处理（重试，换一个工具）

#### （2）核心区别（与Chains对比）

| 对比维度 | Chains       | Agent           |
| ---- | ------------ | --------------- |
| 流程   | 固定、写死        | 动态、自主规划         |
| 思考能力 | 无，按预设执行      | 有，能推理、决策        |
| 工具调用 | 固定调用（若有），无选择 | 自主选择、动态调用       |
| 适用场景 | 简单、标准化任务     | 复杂、多步骤、需工具辅助的任务 |

#### （3）Agent的核心组成

* LLM

* 工具

* 提示词

* Agent Excutor：Agent的执行器，总体架构，负责运行Agent的思考流程、调用工具、处理工具返回结果，最终给出答案

“你查一下公司java岗位的薪资和要求？”

需要查数据库-->调用数据库工具-->提取岗位信息-->整理成回答。

## 五、Function Calling 和MCP

### 1.概念

工具调用是agent的核心，两种核心调用工具方式：Function Calling 和MCP

## 2.Function Calling（Tool Calling）

是大模型嗲用外部工具/函数的标准方式，本质是大模型需要识别到当前的问题需要去调用哪个函数，传入哪些参数，然后执行函数，获取返回结果，再结合结果生成最终回答

```
#核心代码

import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain.agents import create_agent
from langgraph.prebuilt import create_react_agent
import os
from dotenv import load_dotenv

@tool

def xx()

tools = [xx]

agent = create_react_agent(llm, tools) #旧版
agent = create_agent(llm, tools)

async def main(): 
    response = await agent.ainvoke({"messages": "现在几点？"}) 
    print("🤖 AI 回答：", response["messages"][-1].content)

if __name__ == "__main__": 
    asyncio.run(main())
```



任务 1：多功能生活助手（代码见task1.py)

**场景**：你要开发一个"生活助手"Agent，它不仅能查天气，还能做更多实用功能。

**需求**：

1. 使用 `@tool` 定义至少 **4 个工具函数**：
   * `get_weather(city)`: 调用免费的天气 API（如 `https://wttr.in/{city}?format=%C+%t`）获取真实天气数据
   * `convert_currency(amount, from_currency, to_currency)`: 调用免费汇率 API 进行货币换算
   * `get_joke()`: 调用免费笑话 API 获取一个笑话
   * `calculate(expression)`: 用 Python 实现一个安全的数学计算器（add）
2. 使用 `create_react_agent` 创建 Agent
3. 实现一个**交互式对话循环**，用户可以连续提问，输入 `exit` 退出
4. 在终端打印每次工具调用的日志

**验收标准**：

* [ ] 4 个工具都能正常被 Agent 调用
* [ ] 能处理不同类型的问题
* [ ] 对话循环正常运行
* [ ] 终端有工具调用日志
  
  
  
  

## 3.Function Calling（Tool Calling）进阶

支持多轮对话，核心思想：将message做一个拼接

上下文管理策略：

* 固定轮数保留

* 固定max-length，压缩前文

* 根据问题类型，差异化处理

* 根据业务场景而定
  
  
  
  

《培训机构的智能问答机器人》 06_tool_advanced.py

**场景**：你是一个教育培训机构的"学习规划师"，能根据学生信息推荐学习路径。

需求：

1. 使用 `@tool` 定义 **3 个工具函数**：
   * `get_course_info(keyword)`: 模拟课程数据库，根据关键词返回相关课程
   * `assess_level(current, target)`: 评估学生当前水平到目标水平的差距
   * `generate_study_plan(hours_per_day, total_days)`: 根据每天学习小时数和总天数生成学习计划表
2. 使用 `create_agent` 创建 Agent
3. 实现**多轮对话**，支持用户追问 ，messages.append()
4. 工具函数内部打印日志
   
   
   
   
   
   

任务 3：电商智能客服 Agent  

**场景**：你是一个电商平台的智能客服，能处理订单查询、退款、商品推荐等问题。

**需求**：

1. 使用 `@tool` 定义 **5 个工具函数**：
   * `query_order(order_id)`: 查询订单状态
   * `calculate_refund(original_price, discount, days_since_purchase)`: 计算退款金额
   * `recommend_product(category, budget)`: 根据品类和预算推荐商品
   * `check_coupon(product_price)`: 计算最优优惠券组合（满100减10，满200减30，满500减80）
   * `get_shipping_fee(city)`: 计算运费
2. 使用 `create_agent` 创建 Agent
3. 实现对话循环，支持多轮交互
4. **额外要求**：每个工具函数的 docstring 必须足够详细

**验收标准**：

* [ ] 5 个工具都能正常调用

* [ ] 优惠券计算逻辑正确

* [ ] 多轮对话正常
    ORDER_DB = {
  
        "1001": {"status": "已发货", "item": "Python编程入门", "date": "2026-08-01"},
        "1002": {"status": "运输中", "item": "LangChain实战教程", "date": "2026-08-03"},
        "1003": {"status": "已签收", "item": "AI智能体开发指南", "date": "2026-07-25"},
  
    }
  
        if days_since_purchase <= 7:
            refund = actual_paid
            reason = "7天无理由退货，全额退款"
        elif days_since_purchase <= 30:
            refund = actual_paid * 0.8
            reason = "7-30天退货，扣除20%手续费"
        else:
            return "购买已超过30天，不支持退货"
      
        products = {
            "编程书": [{"name": "Python入门", "price": 59}, {"name": "LangChain实战", "price": 89}],
            "AI书": [{"name": "智能体开发", "price": 129}, {"name": "大模型原理", "price": 99}],
            "工具书": [{"name": "Git实战", "price": 49}, {"name": "Docker入门", "price": 69}],
        }
      
        if "北京" in city or "上海" in city:
            base = 5
        elif "省" in city or "市" in city:
            base = 8
        else:
            base = 12

![357a0b09-f508-4ce7-bc4a-e6b9126131e9](file:///C:/Users/qiuxingyu/OneDrive/Pictures/Typedown/357a0b09-f508-4ce7-bc4a-e6b9126131e9.png)

##### 注意点：

①工具 docstring 必须详细！Agent 靠它判断何时调用哪个工具

②调用逻辑和流程可回溯

③准备足量的测试数据（******）



### 4.MCP:

(1)概念：

是多工具并行调用方式，并行处理多个任务，把所有工具的返回结果合并后再生成回答，提高效率。

类似于前后端分离的概念，agent和tool是分离的，所有工具放在一个或者多个服务，起了服务，就可以去调用工具，复合项目开发的高解耦和可扩展维护。

（2）对比

![d25d28d2eec44a6ead8f93a0a8f93628](file:///C:/Users/qiuxingyu/OneDrive/Pictures/Typedown/d25d28d2-eec4-4a6e-ad8f-93a0a8f93628.png?msec=1785979420983)

## （3）实例

server.py

client.py



### 任务6：多个tool挂载在一个mcp-server上

互联网工具 MCP 聚合

**场景**：你要创建一个"万能查询助手"，通过 MCP 接入多个公开免费 API，实现一句话查一切的功能。

**需求**：

1. 创建 `server_internet.py`，暴露 **5 个工具**（调用真实公开免费 API）：
   * `get_ip_info(ip)`: 调用 `http://ip-api.com/json/{ip}` 获取 IP 归属地
   * `get_random_fact()`: 获取一条毒鸡汤
   * `search_wikipedia(keyword)`: 获取维基百科摘要
   * `get_time_zone(location)`: 获取时区和当前时间
   * `get_domain_info(domain)`: 查询域名信息
2. 创建 `task6_internet.py` 实现对话 Agent
3. 网络异常时有合理的错误处理

**验收标准**：

* [ ] 5 个工具都能连接真实 API
* [ ] 网络异常时有合理的错误处理
* [ ] Agent 能正确选择工具

**参考答案**：参见 `server_internet.py`、`task6_internet.py`

**测试问题参考**：| 用户输入 | 预期调用工具 ||---------|-------------|| "查一下 8.8.8.8 的信息" | `get_ip_info` || "给我讲个冷知识" | `get_random_fact` || "查一下 LangChain 是什么" | `search_wikipedia` || "现在东京几点？" | `get_time_zone` || "google.com 的 IP 是多少？" | `get_domain_info` |





### 任务 4：多 MCP Server 数据聚合助手

**场景**：公司有三个独立的 MCP 服务（职位查询、公司信息、薪资计算器），你需要创建一个 Agent 同时接入它们，完成复合查询。

**需求**：

1. 创建 **3 个独立的 server 文件**：
   * `server_jobs.py`: 暴露 `search_jobs(keyword)` 工具
   * `server_company.py`: 暴露 `get_company_info(company_name)` 工具
   * `server_salary.py`: 暴露 `calc_salary(base, experience_years)` 工具（每年涨 8%）
2. 创建 `task4_multi_mcp.py`，使用 `MultiServerMCPClient` 同时连接 3 个服务
3. 使用 `create_agent` 创建 Agent
4. 实现一个能回答复合问题的对话系统

**验收标准**：

* [ ] 3 个 server 能独立启动
* [ ] client 能同时连接 3 个 server
* [ ] Agent 能跨服务组合工具

**参考答案**：参见 `server_jobs.py`、`server_company.py`、`server_salary.py`、`task4_multi_mcp.py`

**测试问题参考**：| 用户输入 | 预期调用工具组合 ||---------|----------------|| "Python 工程师有哪些职位？" | `search_jobs` || "腾讯是做什么的？" | `get_company_info` || "基础月薪 20000，干 3 年后薪资多少？" | `calc_salary` || "Python 工程师在腾讯干 3 年能拿多少？" | `search_jobs` → `get_company_info` → `calc_salary` |



### （3）mcp.run(transport="stdio")transport参数详解

- stdio：客户端拉起一个本地的  MCP-Server子进程，通过进程进行管理和通信
  -优点：零网络配置，本地调用最简单，适合本地工具服务
  -缺点：只能启动本地服务，无法远程服务

- sse：HTTP单向流式
  -通信：客户端发送HTTP请求，服务端持续SSE事件推送，这个请求走POST
  -适合：部署在后端http服务、远程mcp服务
  -需要额外传url参数

- websocket
  -双向实时通信，适合频繁双向交互

- tcp：内网自定义TCP服务，很少用

- in-memory：服务端和客户端需要再同意哦python进程里面，这个用来做测试
  
  

<style> table { border-collapse: collapse; width: 100%; } th, td { border: 1px solid #ccc; padding: 8px; text-align: left; } </style>

| MCP 服务部署形式                    | transport 参数 | 原因                      |
| ----------------------------- | ------------ | ----------------------- |
| 自己电脑本地启动高德 / 飞书 mcp 服务端       | `stdio`      | 调用本地子进程                 |
| 高德官方云端托管 MCP‑Server           | `sse`        | HTTP 远程流式长连接            |
| 服务器部署私有化高德、飞书 MCP，内网 Agent 调用 | sse          | HTTP 好配置、适配 Nginx、HTTPS |
| 企业中台高频双向调用地图 + 机器人消息          | websocket    | 双向通信、低延迟                |

一句话总结
-----

1. 日常高德地图网页 APP：普通 HTTP，实时车辆轨迹用 WebSocket；
2. **大模型调用高德官方云端 MCP 工具，必须 transport="sse"**；
3. 本地搭建的飞书、高德 MCP 服务端用 stdio；远程部署优先 SSE，高频双向业务选 websocket。
   
   

### 示例

task6_internet.py  vs task66.py

sse传输：需要先起server端的服务，再起client以post请求的形式调用mcp服务
两套生产架构对照
--------

### 架构 A（推荐，单机部署）

* 内网服务器：同时运行 Agent + MCP‑Server
* Agent → MCP：stdio 本地管道
* 公司内网员工 → Agent：访问 Agent 对外暴露的 http 接口
* 优点：没有内网端口暴露、防火墙问题、网络波动，稳定性拉满

### 架构 B（多机部署）

* 服务器 A：Agent 主服务
* 服务器 B：独立 MCP‑Server 工具服务
* A、B 处在同一个内网网段
* Agent 访问 MCP：`http://192.168.B的IP:8000/sse`（SSE 网络传输）
* 员工依旧只访问服务器 A 的 Agent 接口

极简记忆口诀
------

> **同机进程用 stdio，跨机内网必 SSE；终端用户只对接 Agent，不碰 MCP 地址**



## 六、多agent实战

一个agent绑定很多工具，模型可能会有一点迷惑，模型的选择困难，与其让大模型在海量的tool寻找工具，不如对这个决策链进行人工干预和策略设计。另一方面，如果是多任务，需要多个agent并行工作，引入multi-agent的机制。



路由agent/意图识别：不实际调用任何agent，只负责分发任务





## 任务 9：旅游规划智能分发系统

**场景**：你为一个旅游 APP 开发了智能问答系统，根据用户的旅游问题，分发给不同的专业顾问。

**需求**：

1. 定义 **5 个顾问 Chain**：
   * `destination`: 目的地顾问
   * `budget`: 预算规划师
   * `transportation`: 交通顾问
   * `food`: 美食顾问
   * `culture`: 文化顾问
2. 主管节点分析用户需求，判断需要哪些顾问参与
3. 支持单个顾问回答和多顾问并发回答
4. 实现一个**旅行计划生成器**：用户输入目的地 + 天数 + 预算，自动调用所有顾问生成完整旅行计划
5. 打印分发决策

**验收标准**：

* [ ] 5 个顾问都能正常工作
* [ ] 能回答多顾问复合问题
* [ ] 旅行计划生成器能整合所有顾问的输出

![7e50e7d2-7d14-4616-abea-48d009902d94](file:///C:/Users/qiuxingyu/OneDrive/Pictures/Typedown/7e50e7d2-7d14-4616-abea-48d009902d94.png)
