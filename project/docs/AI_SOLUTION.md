# 蜀道安全助手 — AI技术方案文档

> **文档状态说明（2026-08-14）**：本文主要记录目标方案和技术选型。当前版本实际使用的 LangChain Agent、证据降级模式、视觉批注和知识库检索边界见 [CURRENT_IMPLEMENTATION.md](./CURRENT_IMPLEMENTATION.md)，未在代码中出现的模型路由、完整混合检索或向量化流程不视为已交付。

> **项目名称**：蜀道安全助手
> **文档版本 | V1.2
> **编写日期**：2026-08-12
> **适用范围**：蜀道集团安全生产管理平台 — AI智能助手模块 & 考试工坊模块

> **说明**：本文档专注 AI 技术方案（大模型选型、Prompt 设计、RAG 架构、知识库构建、向量数据库选型）。技术框架相关内容（架构设计、部署、安全、性能工程实现）已迁移至 [ARCHITECTURE.md](./ARCHITECTURE.md)。

---

## 目录

- [一、项目概述](#一项目概述)
- [二、大模型选型对比分析](#二大模型选型对比分析)
- [三、Prompt模板设计](#三prompt模板设计)
- [四、RAG架构说明](#四rag架构说明)
- [五、知识库构建流程](#五知识库构建流程)
- [六、向量数据库选型](#六向量数据库选型)
- [附录：技术方案总结](#附录技术方案总结)

---

## 一、项目概述

### 1.1 项目背景

蜀道集团是四川省大型交通建设企业，业务涵盖高速公路、铁路、港口等交通基础设施的建设与运营。安全生产是交通建设企业的生命线，涉及大量国家法律法规、行业规范、企业内部制度及操作规程。

当前痛点：
- 安全规范文档数量庞大、检索困难，一线人员难以快速找到所需条款
- 传统关键字搜索匹配度低，无法理解自然语言提问意图
- 安全培训考试依赖人工出题，效率低、覆盖面有限
- 新员工对安全操作规程理解不深，缺乏即时答疑渠道

### 1.2 建设目标

| 模块 | 核心目标 | 关键指标 |
|------|---------|---------|
| AI智能助手 | 基于企业安全知识库的自然语言问答 | 响应时间≤3s(首字)、并发≥50 QPS、支持≥5轮上下文 |
| 考试工坊 | AI自动出题（单选/多选/判断/填空） | 出题准确率≥80%（人工审核）、支持难度配置 |

---

## 二、大模型选型对比分析

### 2.1 候选模型概览

本项目聚焦国内大模型API服务，主要对比三款主流中文大模型：

| 维度 | 文心一言 (ERNIE) | 通义千问 (Qwen) | 智谱GLM |
|------|-----------------|----------------|---------|
| 厂商 | 百度 | 阿里云 | 智谱AI |
| 推荐版本 | ERNIE-4.0-Turbo | Qwen-Plus / Qwen-Max | GLM-4 |
| 上下文窗口 | 8K~128K | 8K~128K | 8K~128K |
| API兼容 | 百度千帆API | 阿里云DashScope | OpenAI兼容格式 |

### 2.2 多维度对比

#### 2.2.1 中文理解能力

| 能力项 | 文心一言 | 通义千问 | 智谱GLM |
|--------|---------|---------|---------|
| 中文语义理解 | ★★★★★ | ★★★★★ | ★★★★☆ |
| 法律/法规文本理解 | ★★★★★ | ★★★★☆ | ★★★★☆ |
| 专业术语准确性 | ★★★★★ | ★★★★☆ | ★★★★☆ |
| 指令遵循能力 | ★★★★☆ | ★★★★★ | ★★★★☆ |
| 长文本处理 | ★★★★☆ | ★★★★★ | ★★★★☆ |

> **说明**：文心一言在中文法律法规文本理解方面表现突出，适合安全规范问答场景；通义千问在指令遵循和结构化输出方面表现优异，适合AI出题场景。

#### 2.2.2 价格对比（参考价格，以实际为准）

| 模型 | 输入价格(元/百万token) | 输出价格(元/百万token) | 免费额度 |
|------|---------------------|---------------------|---------|
| ERNIE-4.0-Turbo | 120 | 120 | 有限 |
| ERNIE-Speed | 免费 | 免费 | 充足 |
| Qwen-Plus | 40 | 120 | 有 |
| Qwen-Turbo | 8 | 24 | 有 |
| GLM-4 | 100 | 100 | 有 |
| GLM-3-Turbo | 5 | 5 | 充足 |

#### 2.2.3 并发与响应

| 维度 | 文心一言 | 通义千问 | 智谱GLM |
|------|---------|---------|---------|
| 最大并发 | 默认QPS=2，可申请提升 | 默认QPS=60 | 默认QPS=10，可提升 |
| SSE流式支持 | ✅ 支持 | ✅ 支持 | ✅ 支持 |
| 首token延迟 | ~1-2s | ~0.5-1.5s | ~0.5-1s |
| Function Call | ✅ 支持 | ✅ 支持 | ✅ 支持 |
| API稳定性 | ★★★★☆ | ★★★★★ | ★★★★☆ |

#### 2.2.4 安全合规

| 维度 | 文心一言 | 通义千问 | 智谱GLM |
|------|---------|---------|---------|
| 内容安全审核 | 内置，严格 | 内置，严格 | 内置，可配置 |
| 数据安全 | 不用于训练(企业版) | 不用于训练(企业版) | 不用于训练(企业版) |
| 备案合规 | ✅ 已备案 | ✅ 已备案 | ✅ 已备案 |

### 2.3 选型决策

```
┌─────────────────────────────────────────────────────────────┐
│                     多模型协同策略                            │
│                                                             │
│  ┌─────────────────┐    主力模型     ┌─────────────────┐    │
│  │  AI智能问答       │──────────────▶│  文心一言         │    │
│  │  (安全法规场景)   │               │  ERNIE-4.0-Turbo│    │
│  └─────────────────┘               └─────────────────┘    │
│                                                             │
│  ┌─────────────────┐    主力模型     ┌─────────────────┐    │
│  │  AI自动出题       │──────────────▶│  通义千问         │    │
│  │  (结构化输出)     │               │  Qwen-Plus       │    │
│  └─────────────────┘               └─────────────────┘    │
│                                                             │
│  ┌─────────────────┐    降级备用     ┌─────────────────┐    │
│  │  降级/高并发场景   │──────────────▶│  智谱GLM-3-Turbo │    │
│  │  (成本控制)       │               │  (性价比高)       │    │
│  └─────────────────┘               └─────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

**最终选型方案**：

| 场景 | 主模型 | 备用模型 | 选型理由 |
|------|--------|---------|---------|
| AI智能问答 | 文心一言 ERNIE-4.0-Turbo | 智谱GLM-4 | 中文法规理解能力强，安全审核严格 |
| AI自动出题 | 通义千问 Qwen-Plus | 文心一言 ERNIE-4.0 | 指令遵循好，JSON结构化输出稳定 |
| Embedding | bge-large-zh（本地部署） | — | 中文嵌入效果好，延迟低，无API成本 |
| Rerank | bge-reranker-large（本地部署） | — | 重排序精度高，本地部署降低延迟 |

### 2.4 大模型API统一封装

采用LangChain框架的ChatModel抽象统一封装多模型API，实现模型切换的透明化：

```python
"""
大模型API统一封装 - 基于LangChain ChatModel抽象
"""
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.chat_models import QianfanChatEndpoint, ChatTongyi, ChatZhipuAI
from typing import AsyncGenerator


class LlmService:
    """大模型服务统一封装，基于LangChain ChatModel"""

    def __init__(self, model: BaseChatModel):
        self.model = model

    def chat(self, messages: list, temperature: float = 0.3) -> str:
        """同步调用"""
        self.model.temperature = temperature
        response = self.model.invoke(messages)
        return response.content

    async def chat_stream(self, messages: list, temperature: float = 0.3) -> AsyncGenerator[str, None]:
        """SSE流式调用（异步生成器）"""
        self.model.temperature = temperature
        async for chunk in self.model.astream(messages):
            if chunk.content:
                yield chunk.content

    def embedding(self, text: str) -> list:
        """Embedding向量化（由独立Embeddings实例提供）"""
        raise NotImplementedError("请使用 EmbeddingService")

"""
模型工厂配置 - 通过LangChain封装国内大模型API
"""
import os


class LlmConfig:
    """大模型配置工厂，创建各厂商LangChain ChatModel实例"""

    @staticmethod
    def ernie_service() -> LlmService:
        """文心一言（百度千帆）"""
        model = QianfanChatEndpoint(
            model="ERNIE-4.0-Turbo-8K",
            qianfan_ak=os.getenv("ERNIE_API_KEY"),
            qianfan_sk=os.getenv("ERNIE_SECRET_KEY"),
        )
        return LlmService(model)

    @staticmethod
    def qwen_service() -> LlmService:
        """通义千问（阿里云DashScope）"""
        model = ChatTongyi(
            model="qwen-plus",
            dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
        )
        return LlmService(model)

    @staticmethod
    def glm_service() -> LlmService:
        """智谱GLM"""
        model = ChatZhipuAI(
            model="glm-4",
            api_key=os.getenv("ZHIPU_API_KEY"),
        )
        return LlmService(model)

"""
模型路由器 - 根据场景选择模型，支持故障自动降级
"""
import logging

logger = logging.getLogger(__name__)


class LlmStrategy:
    """模型路由策略"""
    STRATEGIES = {
        "qa": {"primary": "ernie", "fallback": "glm"},
        "exam_generation": {"primary": "qwen", "fallback": "ernie"},
    }

    @classmethod
    def of(cls, scene: str) -> dict:
        return cls.STRATEGIES.get(scene, {"primary": "ernie", "fallback": "glm"})


class LlmRouter:
    """模型路由器 - 根据场景选择模型，带自动降级"""

    def __init__(self):
        self._services = {
            "ernie": LlmConfig.ernie_service(),
            "qwen": LlmConfig.qwen_service(),
            "glm": LlmConfig.glm_service(),
        }

    def route(self, scene: str) -> LlmService:
        strategy = LlmStrategy.of(scene)
        primary = strategy["primary"]
        fallback = strategy["fallback"]
        try:
            return self._services[primary]
        except Exception as e:
            logger.warning(f"主模型调用失败，降级到备用模型: {e}")
            return self._services[fallback]
```

---

## 三、Prompt模板设计

### 3.1 Prompt设计原则

1. **角色设定明确**：明确AI角色为"蜀道集团安全生产智能助手"，限定回答范围
2. **知识边界约束**：严格基于检索到的知识片段回答，禁止编造
3. **输出格式规范**：结构化输出，便于前端解析和展示
4. **安全审核前置**：在Prompt中嵌入安全约束指令
5. **引用来源标注**：要求AI标注引用的知识来源

### 3.2 AI智能问答 Prompt模板

#### 3.2.1 系统Prompt（System Prompt）

```
你是「蜀道安全助手」，蜀道集团的安全生产智能助手。你的职责是基于企业提供的安全知识库，为员工提供准确的安全生产法规、制度、操作规程等方面的问答服务。

## 核心规则
1. 【知识边界】你只能基于下方<参考知识>中的内容回答问题，严禁使用<参考知识>之外的知识编造答案。
2. 【诚实回答】如果<参考知识>中没有相关信息，请明确回答"当前知识库中暂无相关信息，建议联系安全管理部门咨询"，不要猜测或编造。
3. 【引用来源】回答时请在关键信息后标注引用来源，格式为 [来源: 文档名称-章节]。
4. 【专业准确】使用专业、准确的安全术语，确保法规条款引用正确。
5. 【安全第一】任何涉及安全操作的建议必须保守、合规，不得给出可能危及安全的指导。
6. 【语言风格】使用简洁、专业的中文回答，适当使用条目化排版，便于阅读。

## 参考知识
{retrieved_context}

## 对话历史
{conversation_history}

## 用户问题
{user_question}

请基于以上参考知识回答用户问题。回答格式要求：
- 直接回答问题，不要重复用户的问题
- 关键信息标注引用来源 [来源: 文档名称-章节]
- 如有操作步骤，使用编号列表
- 如有注意事项，使用⚠️标识
```

#### 3.2.2 Python实现 - Prompt模板管理（LangChain ChatPromptTemplate）

```python
"""
Prompt模板管理 - 基于LangChain ChatPromptTemplate
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage


class PromptManager:

    # 智能问答系统Prompt
    QA_SYSTEM_PROMPT = """你是「蜀道安全助手」，蜀道集团的安全生产智能助手。
    你的职责是基于企业提供的安全知识库，为员工提供准确的安全生产问答服务。

    ## 核心规则
    1. 【知识边界】只能基于下方<参考知识>中的内容回答，严禁编造。
    2. 【诚实回答】如果<参考知识>中没有相关信息，请回答：
       "当前知识库中暂无相关信息，建议联系安全管理部门咨询"。
    3. 【引用来源】回答时请在关键信息后标注引用来源，格式为 [来源: 文档名称-章节]。
    4. 【专业准确】使用专业安全术语，确保法规条款引用正确。
    5. 【安全第一】涉及安全操作的建议必须保守、合规。

    ## 参考知识
    {retrieved_context}

    ## 对话历史
    {conversation_history}

    ## 用户问题
    {user_question}

    请基于以上参考知识回答。关键信息标注引用来源 [来源: 文档名称-章节]，
    操作步骤用编号列表，注意事项用⚠️标识。"""

    def __init__(self):
        self.qa_prompt = ChatPromptTemplate.from_template(self.QA_SYSTEM_PROMPT)

    def build_qa_prompt(self, user_question: str,
                        retrieved_context: str,
                        history: list) -> str:
        """构建问答Prompt"""
        return self.qa_prompt.format(
            user_question=user_question,
            retrieved_context=retrieved_context,
            conversation_history=self._format_history(history),
        )

    def _format_history(self, history: list) -> str:
        """格式化对话历史（最近5轮）"""
        if not history:
            return "（无历史对话）"
        # 只取最近5轮（10条消息）
        recent = history[-10:]
        lines = []
        for msg in recent:
            role = "用户" if msg.get("role") == "user" else "助手"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)
```

#### 3.2.3 检索结果拼接格式

```python
def format_retrieved_context(chunks: list) -> str:
    """将检索到的知识片段格式化为Prompt上下文"""
    parts = []
    for i, chunk in enumerate(chunks):
        parts.append(
            f"--- 知识片段 {i + 1} ---\n"
            f"【来源】{chunk['document_name']} - {chunk['section']}\n"
            f"【内容】{chunk['content']}\n"
        )
    return "\n".join(parts)
```

### 3.3 AI出题 Prompt模板

#### 3.3.1 单选题/多选题 Prompt模板

```
你是蜀道集团安全生产培训出题专家。请根据以下知识点和参考材料，生成高质量的{question_type}题目。

## 出题要求
1. 【题型】{question_type}（{option_count}个选项）
2. 【难度等级】{difficulty_level}（简单/中等/困难）
3. 【题目数量】{question_count}道
4. 【知识点】{knowledge_points}
5. 【参考材料】{reference_material}

## 难度标准
- 简单：直接考查基本概念、定义、常识性安全知识
- 中等：需要理解原理、辨析易混淆概念、应用于实际场景
- 困难：综合分析、多知识点交叉、案例推理判断

## 输出格式（严格JSON）
```json
{
  "questions": [
    {
      "type": "single_choice",
      "difficulty": "中等",
      "knowledge_point": "安全生产法-从业人员权利",
      "question": "根据《安全生产法》，从业人员有权对本单位安全生产工作中存在的问题提出批评、(  )、控告。",
      "options": {
        "A": "检举",
        "B": "举报",
        "C": "投诉",
        "D": "建议"
      },
      "answer": "B",
      "explanation": "根据《安全生产法》第五十七条规定，从业人员有权对本单位安全生产工作中存在的问题提出批评、检举、控告；有权拒绝违章指挥和强令冒险作业。本题考查从业人员的权利，答案为B。注意区分'检举'与'举报'的用词准确性。"
    }
  ]
}
```

## 注意事项
- 题目表述准确、无歧义
- 干扰项合理，具有迷惑性但不能产生歧义
- 正确答案分布均匀
- 解析必须详细，说明正确答案的依据和错误选项排除理由
- 引用法规时需标注具体条款

## 知识点
{knowledge_points}

## 参考材料
{reference_material}

请生成{question_count}道{difficulty_level}难度的{question_type}题目，严格按JSON格式输出。
```

#### 3.3.2 判断题 Prompt模板

```
你是蜀道集团安全生产培训出题专家。请根据以下知识点生成判断题。

## 出题要求
1. 【题型】判断题（正确/错误）
2. 【难度等级】{difficulty_level}
3. 【题目数量】{question_count}道
4. 【知识点】{knowledge_points}

## 难度标准
- 简单：基本概念判断、常见安全常识
- 中等：法规条款理解、操作规程辨析
- 困难：易混淆概念、例外情形、综合判断

## 输出格式（严格JSON）
```json
{
  "questions": [
    {
      "type": "true_false",
      "difficulty": "中等",
      "knowledge_point": "安全生产法-三同时制度",
      "question": "建设项目的安全设施，必须与主体工程同时设计、同时施工、同时投入生产和使用。",
      "answer": "正确",
      "explanation": "根据《安全生产法》第三十一条规定，建设项目安全设施必须与主体工程同时设计、同时施工、同时投入生产和使用，简称'三同时'制度。安全设施投资应当纳入建设项目概算。"
    }
  ]
}
```

## 注意事项
- 错误题目的错误点必须明确，不能含糊
- 避免使用"总是""从不"等绝对化表述制造陷阱
- 解析需说明判断依据，对错误题目需指出错误之处

请生成{question_count}道{difficulty_level}难度的判断题，严格按JSON格式输出。
```

#### 3.3.3 填空题 Prompt模板

```
你是蜀道集团安全生产培训出题专家。请根据以下知识点生成填空题。

## 出题要求
1. 【题型】填空题（每题1-2个空）
2. 【难度等级】{difficulty_level}
3. 【题目数量】{question_count}道
4. 【知识点】{knowledge_points}

## 输出格式（严格JSON）
```json
{
  "questions": [
    {
      "type": "fill_blank",
      "difficulty": "简单",
      "knowledge_point": "消防安全-灭火器使用",
      "question": "使用干粉灭火器灭火时，应对准火焰的______喷射。",
      "answers": ["根部"],
      "explanation": "使用干粉灭火器时，应拔出保险销，握住喷管，对准火焰根部喷射，由近及远，快速推进，直至火焰全部扑灭。注意不要对准火焰顶部喷射，否则灭火效果不佳。"
    }
  ]
}
```

## 注意事项
- 空白处应填入专业术语或关键数字，不宜填入虚词
- 每空答案唯一，避免歧义
- 解析需补充完整知识点背景

请生成{question_count}道{difficulty_level}难度的填空题，严格按JSON格式输出。
```

#### 3.3.4 AI出题 Python实现

```python
"""
AI出题服务 - 基于FastAPI + LangChain
"""
import json
import re
import logging
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)


class AiQuestionService:

    def __init__(self, llm_router, prompt_manager, rag_service):
        self.llm_router = llm_router
        self.prompt_manager = prompt_manager
        self.rag_service = rag_service

    def generate_questions(self, req: dict) -> list:
        """AI生成题目"""
        # 1. 根据知识点检索参考材料
        knowledge_points = "、".join(req["knowledge_points"])
        chunks = self.rag_service.retrieve(knowledge_points, 5)
        reference_material = self._format_reference(chunks)

        # 2. 构建Prompt
        prompt = self.prompt_manager.build_exam_prompt(
            question_type=req["question_type"],     # 题型
            difficulty=req["difficulty"],           # 难度
            count=req["count"],                    # 数量
            knowledge_points=knowledge_points,      # 知识点
            reference_material=reference_material   # 参考材料
        )

        # 3. 调用大模型（出题场景使用通义千问）
        llm = self.llm_router.route("exam_generation")
        messages = [
            SystemMessage(content="你是安全生产出题专家，严格按JSON格式输出。"),
            HumanMessage(content=prompt),
        ]
        response = llm.chat(messages, temperature=0.7)  # 适度随机，保证题目多样性

        # 4. 解析JSON结果
        questions = self._parse_questions(response)

        # 5. 后处理：校验答案、去重
        return self._validate_and_dedup(questions)

    def _parse_questions(self, llm_response: str) -> list:
        """题目解析与校验"""
        # 提取JSON部分
        json_str = self._extract_json(llm_response)
        resp = json.loads(json_str)

        valid_questions = []
        for q in resp.get("questions", []):
            # 校验必填字段
            if not q.get("question") or q.get("answer") is None:
                logger.warning(f"题目字段不完整，跳过: {q.get('question')}")
                continue
            # 校验选项完整性
            if self._is_choice_question(q["type"]) and not self._validate_options(q):
                logger.warning(f"选项不完整，跳过: {q.get('question')}")
                continue
            valid_questions.append(q)
        return valid_questions
```

---

## 四、RAG架构说明

### 4.1 RAG整体流程

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              RAG 完整流程                                 │
│                                                                          │
│  ════════════════ 离线知识库构建 ════════════════                         │
│                                                                          │
│  ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐    │
│  │ 文档加载 │───▶│ 文本分块 │───▶│ 向量化  │───▶│ 存入向量 │───▶│ 索引构建│    │
│  │        │    │ Chunking│    │Embedding│   │  数据库  │    │  Index  │    │
│  └────────┘    └────────┘    └────────┘    └────────┘    └────────┘    │
│                                                                          │
│  ════════════════ 在线问答检索 ════════════════                           │
│                                                                          │
│  ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐    │
│  │ 用户提问 │───▶│ 查询向量化│───▶│ 向量检索│───▶│ 重排序  │───▶│Prompt  │    │
│  │        │    │        │    │Top-K   │    │Rerank  │    │ 构建    │    │
│  └────────┘    └────────┘    └───┬────┘    └────────┘    └───┬────┘    │
│                                   │                          │          │
│                              ┌────▼────┐               ┌────▼────┐     │
│                              │ 混合检索  │               │ 大模型   │     │
│                              │向量+关键字│               │ 生成回答 │     │
│                              └─────────┘               └─────────┘     │
└──────────────────────────────────────────────────────────────────────────┘
```

### 4.2 各阶段详解

#### 4.2.1 文档加载（Document Loading）

支持多种文档格式的解析加载：

```python
"""
文档加载器 - 基于LangChain DocumentLoader，支持多格式文档解析
"""
import os
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader, Docx2txtLoader, TextLoader, UnstructuredMarkdownLoader
)


class DocumentLoaderService:

    def load(self, file_path: str) -> list[Document]:
        """根据文件类型加载文档"""
        ext = os.path.splitext(file_path)[1].lower().lstrip(".")
        loaders = {
            "pdf": lambda: PyPDFLoader(file_path),
            "docx": lambda: Docx2txtLoader(file_path),
            "doc": lambda: Docx2txtLoader(file_path),
            "txt": lambda: TextLoader(file_path, encoding="utf-8"),
            "md": lambda: UnstructuredMarkdownLoader(file_path),
        }
        if ext not in loaders:
            raise ValueError(f"不支持的文件格式: {ext}")

        loader = loaders[ext]()
        docs = loader.load()

        # 补充元数据
        file_name = os.path.basename(file_path)
        for i, doc in enumerate(docs):
            doc.metadata.setdefault("source", file_path)
            doc.metadata.setdefault("file_name", file_name)
            doc.metadata.setdefault("page", i + 1)

        return docs
```

#### 4.2.2 文本分块（Chunking）

采用**递归字符分块策略**，兼顾语义完整性和块大小控制：

```python
"""
文本分块器 - 基于LangChain RecursiveCharacterTextSplitter
策略：递归字符分割 + 滑动窗口重叠
"""
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


class TextChunkerService:

    # 分割符优先级（从高到低）
    SEPARATORS = [
        "\n## ",       # Markdown二级标题
        "\n### ",      # Markdown三级标题
        "\n\n",        # 段落分隔
        "\n",          # 换行
        "。",          # 中文句号
        "；",          # 中文分号
        "，",          # 中文逗号
        " ",           # 空格
        "",            # 字符级
    ]

    def __init__(self):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,          # 每块目标字数
            chunk_overlap=100,       # 块间重叠字数
            separators=self.SEPARATORS,
        )

    def chunk(self, document: Document) -> list[Document]:
        """递归分块"""
        return self.splitter.split_documents([document])
```

**分块策略说明**：

```
原始文档（约5000字）
│
├── 按 "## " 标题分割 → 大段落
│   ├── 第1章 安全生产法概述（2000字）
│   │   ├── 按 "\n\n" 段落分割
│   │   │   ├── 段落1（600字）→ 超过500字限制
│   │   │   │   ├── 按 "。" 句号分割
│   │   │   │   ├── 句子1~3 合并 → Chunk 1（约480字）
│   │   │   │   └── 句子3~5 合并 → Chunk 2（约450字）[与Chunk1重叠100字]
│   │   │   └── 段落2（400字）→ Chunk 3
│   │   └── ...
│   └── 第2章 ...
```

#### 4.2.3 向量化（Embedding）

使用 BGE 模型进行中文文本向量化：

```python
"""
向量化服务 - 基于LangChain HuggingFaceEmbeddings
"""
from langchain_community.embeddings import HuggingFaceEmbeddings


class EmbeddingService:

    # BGE-large-zh 维度
    VECTOR_DIM = 1024

    def __init__(self):
        self.embedding_model = HuggingFaceEmbeddings(
            model_name="BAAI/bge-large-zh-v1.5",
            model_kwargs={"device": "cuda"},  # CPU环境改为 "cpu"
        )

    def embed(self, text: str) -> list:
        """文本向量化"""
        return self.embedding_model.embed_query(text)

    def embed_batch(self, texts: list) -> list:
        """批量向量化（提升吞吐）"""
        return self.embedding_model.embed_documents(texts)
```

**Embedding模型选型对比**：

| 模型 | 维度 | 中文效果 | 部署方式 | 延迟 |
|------|------|---------|---------|------|
| bge-large-zh-v1.5 | 1024 | ★★★★★ | 本地GPU | ~50ms |
| bge-base-zh-v1.5 | 768 | ★★★★☆ | 本地CPU可跑 | ~30ms |
| text-embedding-ada-002 | 1536 | ★★★☆☆ | OpenAI API | ~200ms |
| M3E-large | 1024 | ★★★★☆ | 本地GPU | ~50ms |

> **选型**：bge-large-zh-v1.5，中文嵌入效果在C-MTEB榜单表现优异，本地部署延迟低、无API成本。

#### 4.2.4 向量检索（Retrieval）

采用**混合检索策略**：向量检索 + 关键字检索（BM25），兼顾语义匹配和精确匹配：

```python
"""
混合检索服务 - 基于LangChain VectorStore
策略：向量检索 + 关键字检索（BM25），兼顾语义匹配和精确匹配
"""
import asyncio
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever


class HybridRetrievalService:

    def __init__(self, vector_store: Chroma, embedding_service):
        self.vector_store = vector_store
        self.embedding_service = embedding_service

    async def hybrid_search(self, query: str, top_k: int) -> list:
        """混合检索：向量 + 关键字"""
        # 并行执行两种检索
        vector_results, keyword_results = await asyncio.gather(
            self._vector_search(query, top_k * 2),
            self._keyword_search(query, top_k * 2),
        )

        # 融合排序（RRF算法）
        return self._rrf_merge(vector_results, keyword_results, top_k)

    async def _vector_search(self, query: str, top_k: int) -> list:
        """LangChain VectorStore 向量检索"""
        return self.vector_store.similarity_search_with_score(query, k=top_k)

    async def _keyword_search(self, query: str, top_k: int) -> list:
        """BM25关键字检索"""
        retriever = BM25Retriever.from_documents(self._get_all_docs())
        retriever.k = top_k
        return retriever.get_relevant_documents(query)

    def _rrf_merge(self, vector_results: list, keyword_results: list, top_k: int) -> list:
        """Reciprocal Rank Fusion (RRF) 融合算法"""
        k = 60.0  # RRF参数
        scores = {}
        result_map = {}

        # 向量检索结果排名融合
        for i, r in enumerate(vector_results):
            key = r[0].page_content[:50]  # 用内容前50字作为唯一键
            scores[key] = scores.get(key, 0) + 1.0 / (k + i + 1)
            result_map.setdefault(key, r)

        # 关键字检索结果排名融合
        for i, r in enumerate(keyword_results):
            key = r.page_content[:50]
            scores[key] = scores.get(key, 0) + 1.0 / (k + i + 1)
            result_map.setdefault(key, r)

        # 按融合分数排序
        sorted_keys = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:top_k]
        return [result_map[key] for key in sorted_keys]
```

#### 4.2.5 重排序（Reranking）

向量检索召回后，使用 Cross-Encoder 模型对 Top-K 结果进行精排：

```python
"""
重排序服务 - 使用 bge-reranker-large 模型（CrossEncoder）对检索结果精排
"""
from sentence_transformers import CrossEncoder


class RerankService:

    RERANK_THRESHOLD = 0.3  # 阈值过滤

    def __init__(self):
        self.reranker_model = CrossEncoder("BAAI/bge-reranker-large")

    def rerank(self, query: str, candidates: list, top_n: int) -> list:
        """
        对检索结果重排序

        :param query:      用户查询
        :param candidates: 候选知识块（Top-10）
        :param top_n:      保留数量（Top-5）
        """
        # 计算query与每个候选的相关性分数
        pairs = [(query, doc.page_content) for doc in candidates]
        scores = self.reranker_model.predict(pairs)

        # 按分数降序排序
        scored = list(zip(candidates, scores))
        scored.sort(key=lambda x: x[1], reverse=True)
        scored = scored[:top_n]

        # 过滤低分结果
        return [doc for doc, score in scored if score > self.RERANK_THRESHOLD]
```

**为什么需要重排序？**

```
向量检索（Bi-Encoder）              重排序（Cross-Encoder）
                                    
  Query ──▶ [Embedding]              Query ──┐
                                          ├──▶ [Cross-Encoder] ──▶ Score
  Chunk ──▶ [Embedding]              Chunk ──┘
                                    
  独立编码，速度快                     联合编码，精度高
  适合大规模召回                      适合小规模精排
  召回 Top-10                        精排 Top-5
```

#### 4.2.6 生成（Generation）

基于检索结果和历史对话，构建Prompt调用大模型生成回答：

```python
"""
RAG生成服务 - 基于LangChain RAG链（LCEL表达式）
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser


class RagGenerateService:

    def __init__(self, llm_router, prompt_manager, conversation_service, rag_service):
        self.llm_router = llm_router
        self.prompt_manager = prompt_manager
        self.conversation_service = conversation_service
        self.rag_service = rag_service

    async def rag_answer_stream(self, session_id: str, question: str):
        """RAG问答 - SSE流式输出（异步生成器）"""
        # 1. 检索知识
        chunks = await self.rag_service.retrieve(question, 5)

        # 2. 获取对话历史
        history = self.conversation_service.get_history(session_id, 5)

        # 3. 构建Prompt
        prompt = self.prompt_manager.build_qa_prompt(
            user_question=question,
            retrieved_context=self._format_context(chunks),
            history=history,
        )

        # 4. 调用大模型流式输出（LangChain astream）
        llm = self.llm_router.route("qa")
        messages = [HumanMessage(content=prompt)]

        async for token in llm.chat_stream(messages, temperature=0.1):
            yield f"data: {token}\n\n"

        # 5. 发送引用来源
        sources = self._build_sources(chunks)
        yield f"event: sources\ndata: {sources}\n\n"

        # 6. 保存对话历史
        self.conversation_service.save_turn(session_id, question, chunks)

    def _build_sources(self, chunks: list) -> list:
        """构建引用来源信息"""
        return [
            {
                "document_name": c.metadata.get("file_name", ""),
                "section": c.metadata.get("section", ""),
                "content": c.page_content,
            }
            for c in chunks
        ]
```

### 4.3 RAG完整链路编排

```python
"""
RAG编排服务 - 基于LangChain LCEL表达式串联完整RAG流程
"""
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.output_parsers import StrOutputParser


class RagOrchestrator:

    def __init__(self, embedding_service, retrieval_service,
                 rerank_service, generate_service):
        self.embedding_service = embedding_service
        self.retrieval_service = retrieval_service
        self.rerank_service = rerank_service
        self.generate_service = generate_service

    async def retrieve(self, query: str, top_n: int) -> list:
        """完整RAG检索流程"""
        # Step 1: 查询向量化（LangChain Embeddings）
        query_vector = self.embedding_service.embed(query)

        # Step 2: 混合检索 (Top-10) - LangChain VectorStore + BM25
        candidates = await self.retrieval_service.hybrid_search(query, 10)

        # Step 3: 重排序 (Top-5) - CrossEncoder
        reranked = self.rerank_service.rerank(query, candidates, top_n)

        # Step 4: 返回最终结果
        return reranked
```

---

## 五、知识库构建流程

### 5.1 知识库内容规划

```
┌─────────────────────────────────────────────────────────┐
│                  蜀道安全知识库内容体系                    │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ 国家法律法规  │  │ 行业标准规范   │  │ 企业内部制度  │   │
│  │             │  │              │  │              │   │
│  │ ·安全生产法  │  │ ·JTG F90公路  │  │ ·安全管理办法 │   │
│  │ ·建筑法      │  │  工程施工安全 │  │ ·安全责任制度 │   │
│  │ ·消防法      │  │  规范         │  │ ·安全检查制度 │   │
│  │ ·职业病防治法│  │ ·JTG H10公路  │  │ ·安全教育制度 │   │
│  │ ·刑法(安全   │  │  养护规范     │  │ ·事故报告制度 │   │
│  │  相关条款)   │  │ ·GB 6722爆破  │  │              │   │
│  │             │  │  安全规程     │  │              │   │
│  └─────────────┘  └──────────────┘  └──────────────┘   │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ 安全操作规程  │  │ 应急预案      │  │ 事故案例分析  │   │
│  │             │  │              │  │              │   │
│  │ ·高处作业    │  │ ·综合应急预案 │  │ ·坍塌事故     │   │
│  │ ·动火作业    │  │ ·专项应急预案 │  │ ·高处坠落事故 │   │
│  │ ·临时用电    │  │ ·现场处置方案 │  │ ·机械伤害事故 │   │
│  │ ·起重吊装    │  │              │  │ ·触电事故     │   │
│  │ ·有限空间    │  │              │  │ ·火灾爆炸事故 │   │
│  └─────────────┘  └──────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 5.2 知识库处理流程

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ 文档收集  │───▶│ 格式转换  │───▶│ 内容清洗  │───▶│ 元数据标注│
│          │    │          │    │          │    │          │
│·法规原文  │    │·PDF→文本 │    │·去除页眉  │    │·文档类型  │
│·制度文件  │    │·Word→文本│    │·去除水印  │    │·适用范围  │
│·规程手册  │    │·图片OCR  │    │·修复断句  │    │·版本号    │
│·案例报告  │    │·表格提取  │    │·统一编码  │    │·生效日期  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
                                                       │
                                                       ▼
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ 存入SQLite│◀───│ 向量入库  │◀───│ 向量化    │◀───│ 文本分块  │
│ (结构化)  │    │ (Chroma) │    │ (Embedding)│   │ (Chunking)│
│          │    │          │    │          │    │          │
│·文档元信息│    │·向量索引  │    │·bge模型  │    │·递归分割  │
│·分块原文  │    │·元数据   │    │·1024维   │    │·500字/块 │
│·审核状态  │    │          │    │          │    │·100字重叠│
└──────────┘    └──────────┘    └──────────┘    └──────────┘
```

### 5.3 知识库管理 Python实现

```python
"""
知识库管理服务
"""
from pathlib import Path
from fastapi import UploadFile
from langchain_community.document_loaders import PDFPlumberLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from sqlalchemy.orm import Session

# 文件后缀 -> LangChain Loader 映射
LOADER_MAP = {
    ".pdf": PDFPlumberLoader,
    ".docx": Docx2txtLoader,
}


class KnowledgeBaseService:
    """知识库管理服务：上传文档、分块、向量化、入库"""

    def __init__(self, db: Session, vector_store: Chroma):
        self.db = db
        self.vector_store = vector_store
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100,
            separators=["\n\n", "\n", "。", "；", " "],
        )

    async def upload_and_index(self, file: UploadFile, meta: dict) -> None:
        """上传文档并构建知识库"""
        # 1. 保存文档记录
        doc = await self._save_document(file, meta)

        # 2. 加载文档（根据文件后缀选择 Loader）
        loader_cls = LOADER_MAP.get(Path(file.filename).suffix.lower())
        if loader_cls is None:
            raise ValueError(f"不支持的文件类型: {file.filename}")
        documents = loader_cls(doc.file_path).load()

        # 3. 分块（递归字符分割，500字/块，100字重叠）
        chunks = self.text_splitter.split_documents(documents)
        for chunk in chunks:
            chunk.metadata.update({
                "document_id": doc.id,
                "document_name": doc.name,
                "doc_type": meta.get("doc_type", "GENERAL"),
            })

        # 4 & 5. 存入SQLite（原文管理）
        self._save_chunks(doc.id, chunks)

        # 6. 批量向量化并存入Chroma（向量索引）
        #    LangChain VectorStore 会自动调用 Embeddings 进行向量化
        self.vector_store.add_documents(chunks)

        # 7. 更新文档状态
        doc.status = "INDEXED"
        self.db.commit()

    def reindex_document(self, doc_id: int) -> None:
        """增量更新 - 替换文档时重新索引"""
        # 1. 删除旧向量（按 document_id 过滤）
        self.vector_store.delete(expr=f"document_id == {doc_id}")

        # 2. 删除旧分块记录
        self._delete_chunks_by_doc_id(doc_id)

        # 3. 重新加载、分块、向量化、入库
        doc = self._get_document(doc_id)
        self.upload_and_index(doc.file_path, doc.meta)
```

### 5.4 知识库更新机制

| 更新类型 | 触发方式 | 处理策略 | 预期延迟 |
|---------|---------|---------|---------|
| 新增文档 | 管理员上传 | 异步处理：加载→分块→向量化→入库 | <5分钟 |
| 修改文档 | 管理员替换 | 删除旧向量→重新索引 | <5分钟 |
| 删除文档 | 管理员删除 | 删除SQLite记录+Chroma向量 | <1分钟 |
| 法规更新 | 定时任务检查 | 对比版本号→自动通知→人工确认更新 | T+1 |
| 全量重建 | 手动触发 | 清空索引→全量重新向量化 | 视数据量 |

```python
"""
知识库定时检查任务 - 检查法规更新
使用 APScheduler 实现定时任务
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.knowledge import KnowledgeDocument
from app.services.notification import NotificationService
from app.services.regulation_api import RegulationApiService

scheduler = AsyncIOScheduler()


@scheduler.scheduled_job(
    CronTrigger(hour=2, minute=0),  # 每天凌晨2点
    id="check_regulation_updates",
)
async def check_regulation_updates(db: Session):
    """检查法规更新，发现新版本时通知管理员"""
    # 1. 查询所有法规类文档
    regulations = db.execute(
        select(KnowledgeDocument).where(
            KnowledgeDocument.doc_type == "REGULATION"
        )
    ).scalars().all()

    regulation_api = RegulationApiService()
    notifier = NotificationService(db)

    for doc in regulations:
        # 2. 对比外部数据源的版本号
        latest_version = await regulation_api.check_latest_version(
            doc.external_id
        )

        if doc.version != latest_version:
            # 3. 通知管理员确认更新
            await notifier.notify_admin(
                title=f"{doc.name} 有新版本: {latest_version}",
                url=f"/knowledge/pending-update?docId={doc.id}",
            )


# 在 FastAPI 启动事件中注册
# @app.on_event("startup")
# async def startup_event():
#     scheduler.start()
```

---

## 六、向量数据库选型

### 6.1 方案概述

本项目选用 **Chroma** 作为向量数据库。相比需要独立部署服务的 Milvus 和仅作为检索库的 Faiss，Chroma 作为嵌入式向量数据库，与 SQLite 配合使用，使得整个系统无需额外的基础设施服务，部署运维极为简单。

Chroma 核心特性：

| 特性 | 说明 |
|------|------|
| **部署方式** | 嵌入式运行（Python pip install），无需独立服务 |
| **存储方式** | 本地文件持久化，数据随项目迁移 |
| **索引类型** | HNSW（Hierarchical Navigable Small World），检索速度快 |
| **元数据过滤** | 支持 where 条件过滤，可按文档类型/适用范围筛选 |
| **动态更新** | 支持随时增删改文档，无需重建索引 |
| **Python SDK** | ✅ 官方原生支持，与 FastAPI 无缝集成 |
| **存储容量** | 百万级向量，满足知识库长期增长需求 |
| **运维复杂度** | 极低，零运维成本 |

### 6.2 Chroma 方案优势

**✅ 轻量级嵌入式部署**
- pip install 即可使用，无需 Docker 拉取额外镜像
- 数据存储在本地文件系统，备份迁移简单
- 与 SQLite 同为嵌入式数据库，技术栈高度统一

**✅ Python 生态原生支持**
- 官方 Python SDK，API 设计简洁直观
- 与 LangChain 深度集成（langchain_chroma 包）
- 完全适配 FastAPI 异步架构

**✅ 生产可用**
- HNSW 索引算法，百万级向量检索延迟 <100ms
- 支持元数据过滤，满足按文档类型筛选需求
- 持久化存储，数据不丢失

**✅ 极低运维成本**
- 无需 etcd、MinIO、Pulsar 等依赖组件
- 无需独立数据库服务
- 单进程运行，资源占用少

### 6.3 选型决策

```
┌─────────────────────────────────────────────────────────┐
│                  向量数据库选型决策                       │
│                                                         │
│  需求分析:                                               │
│  · 知识库规模: 初始~10万块，未来增长至~50万块              │
│  · 并发要求: ≥50 QPS                                     │
│  · 元数据过滤: 需按文档类型、适用范围过滤                  │
│  · 动态更新: 支持随时增删改文档                           │
│  · 部署要求: 轻量级，无需额外基础设施                      │
│  · Python生态: 后端为FastAPI                             │
│                                                         │
│  决策:                                                   │
│  ┌─────────────────────────────────────────────────┐     │
│  │  统一方案: Chroma（嵌入式向量数据库）              │     │
│  │  · 本地文件持久化，零运维成本                     │     │
│  │  · HNSW索引，百万级检索 <100ms                    │     │
│  │  · 与SQLite构成统一的嵌入式数据层                 │     │
│  │  · langchain_chroma 原生集成                     │     │
│  └─────────────────────────────────────────────────┘     │
│                                                         │
│  理由:                                                   │
│  1. Chroma满足所有核心需求（规模、并发、元数据、动态更新）  │
│  2. 嵌入式部署，与SQLite技术栈高度统一                    │
│  3. 无需Docker额外服务，部署简化到极致                     │
│  4. 官方Python SDK与FastAPI集成成熟                     │
│  5. 适合中小规模知识库（百万级向量）                       │
└─────────────────────────────────────────────────────────┘
```

### 6.4 Chroma 集成实现

```python
"""
Chroma向量存储服务
基于 langchain_chroma 集成，封装集合初始化、检索、插入
"""
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

COLLECTION_NAME = "safety_knowledge"
VECTOR_DIM = 1024  # bge-large-zh 维度
PERSIST_DIRECTORY = "./chroma_data"  # Chroma 本地持久化目录


def create_vector_store(
    embeddings: HuggingFaceEmbeddings,
) -> Chroma:
    """
    创建/获取 Chroma 向量存储实例
    - 数据持久化到本地文件系统
    - 使用 HNSW 索引 + 余弦相似度
    """
    return Chroma(
        embedding_function=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=PERSIST_DIRECTORY,
        collection_metadata={
            "hnsw:space": "cosine",          # 余弦相似度
            "hnsw:M": 16,                    # HNSW 图连接数
            "hnsw:construction_ef": 256,     # 构建时的搜索范围
        },
    )


class ChromaVectorStoreService:
    """向量检索服务：封装相似度搜索与元数据过滤"""

    def __init__(self, vector_store: Chroma):
        self.vector_store = vector_store

    def similarity_search(
        self,
        query: str,
        top_k: int = 10,
        doc_types: list[str] | None = None,
    ) -> list[Document]:
        """
        向量检索（带元数据过滤）
        - query: 用户提问文本
        - top_k: 返回的Top-K结果数
        - doc_types: 文档类型过滤，如 ["REGULATION", "STANDARD"]
        """
        # 构建过滤条件
        filter_dict = None
        if doc_types:
            filter_dict = {"doc_type": {"$in": doc_types}}

        # LangChain Chroma 相似度搜索（内部自动向量化 + HNSW检索）
        results = self.vector_store.similarity_search(
            query=query,
            k=top_k,
            filter=filter_dict,                     # 元数据过滤
        )
        return results

    def add_documents(self, documents: list[Document]) -> list[str]:
        """
        批量插入向量
        - documents: 已分块且带元数据的 Document 列表
        - LangChain 会自动调用 Embeddings 向量化并写入 Chroma
        """
        return self.vector_store.add_documents(documents)

    def delete_by_document_id(self, document_id: int) -> None:
        """按文档ID删除所有关联向量（增量更新时清理旧数据）"""
        self.vector_store.delete(
            filter={"document_id": document_id}
        )
```

---

## 附录：技术方案总结

### 核心技术决策一览

| 决策项 | 选型 | 核心理由 |
|--------|------|---------|
| 问答大模型 | 文心一言 ERNIE-4.0-Turbo | 中文法规理解最强 |
| 出题大模型 | 通义千问 Qwen-Plus | 结构化输出稳定 |
| Embedding模型 | bge-large-zh-v1.5 | 中文嵌入效果优、本地部署 |
| 向量数据库 | Chroma | 嵌入式部署、与SQLite统一技术栈、零运维 |
| 重排序模型 | bge-reranker-large | 精排提升检索准确率 |
| 流式输出 | SSE | 无需WebSocket、兼容性好 |
| 缓存方案 | cachetools 本地TTLCache | 轻量级、无需外部服务 |

### 关键性能指标达成路径

```
首字响应 ≤3s 达成路径:
  Embedding缓存命中(~10ms)
  + Chroma HNSW检索(~200ms)
  + BGE Rerank(~100ms)
  + Prompt构建(~10ms)
  + 大模型首Token(~1-2s)
  = 总计 ~1.3-2.3s ✅

并发 ≥50 QPS 达成路径:
  uvicorn多worker异步并发
  + 本地缓存命中率30%+(减少30%大模型调用)
  + 异步非阻塞(SSE不占线程)
  + 模型API QPS提升申请
  = 有效并发 ~60-80 QPS ✅
```

---

> **文档结束** | 蜀道安全助手 AI技术方案 V1.1
>
> 技术框架相关内容（架构设计、模块技术设计、安全架构、部署架构、性能策略）请参见 [ARCHITECTURE.md](./ARCHITECTURE.md)。
