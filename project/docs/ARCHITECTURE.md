---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 619a68374c198f2d1dccd9a31deded68_6e5532ff95f811f181ac525400f8a581
    ReservedCode1: NPpZHgNnLfKb3FkFytx70SJAdX0pLiqxVGAEPW+O5pif2iEc38ZSpAdLTjEDigs0lFncLDRSmHUwoM2rVSu252/LyfnMJqZOajYpXdfkDPqU7NoV5kbYJ1O9ep6MoIDtW6sjuBe3m/dnkcb72I8qa4chesbjO8Z00qFj6RpOpovJobrXLK/+zSohV10=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 619a68374c198f2d1dccd9a31deded68_6e5532ff95f811f181ac525400f8a581
    ReservedCode2: NPpZHgNnLfKb3FkFytx70SJAdX0pLiqxVGAEPW+O5pif2iEc38ZSpAdLTjEDigs0lFncLDRSmHUwoM2rVSu252/LyfnMJqZOajYpXdfkDPqU7NoV5kbYJ1O9ep6MoIDtW6sjuBe3m/dnkcb72I8qa4chesbjO8Z00qFj6RpOpovJobrXLK/+zSohV10=
---

# 蜀道安全助手 — 技术框架文档

> **文档状态说明（2026-08-14）**：本文包含目标架构与容量规划，其中多模型路由、完整混合检索、CrossEncoder、Redis 等不代表当前版本已经实现。当前运行架构、数据读写边界和真实技术链路见 [CURRENT_IMPLEMENTATION.md](./CURRENT_IMPLEMENTATION.md)。

> **项目名称**：蜀道安全助手
> **文档版本 | V1.2
> **编写日期 | 2026-08-13
> **适用范围**：蜀道集团安全生产管理平台 — 全模块技术框架

---

## 目录

- [一、项目背景与目标](#一项目背景与目标)
- [二、项目代码结构](#二项目代码结构)
- [三、系统总体架构](#三系统总体架构)
- [四、技术栈详解](#四技术栈详解)
- [五、模块技术设计](#五模块技术设计)
- [六、AI 与 RAG 架构](#六ai-与-rag-架构)
- [七、数据架构设计](#七数据架构设计)
- [八、安全架构](#八安全架构)
- [九、部署架构](#九部署架构)
- [十、性能策略](#十性能策略)
- [十一、核心技术决策总结](#十一核心技术决策总结)

---

## 一、项目背景与目标

### 1.1 项目背景

蜀道集团是四川省大型交通建设企业，业务涵盖高速公路、铁路、港口等交通基础设施的建设与运营。安全生产是企业的生命线，面临以下核心痛点：

- **隐患管理效率低**：上报依赖纸质/微信群，信息流转慢、闭环追踪难
- **安全知识获取难**：一线员工缺乏即时权威解答渠道，依赖经验判断
- **培训考核成本高**：传统线下培训覆盖面有限，人工出题效率低
- **数据沉淀不足**：隐患数据分散，缺乏系统化分析手段

### 1.2 建设目标

| 维度 | 目标 | 关键指标 |
|------|------|---------|
| 隐患管理 | 全生命周期数字化闭环 | 闭环率 ≥ 95% |
| AI 智能问答 | 基于知识库的自然语言问答 | 首字响应 ≤ 3s，并发 ≥ 50 QPS，≥ 5 轮上下文 |
| 考试工坊 | AI 自动出题与在线考试 | 出题准确率 ≥ 80%，覆盖全员 |
| 系统整体 | 高并发支撑 | ≥ 200 并发用户 |

---

## 二、项目代码结构

### 2.1 目录总览

基于 `project-root/` 实际目录结构，项目采用 **Monorepo 前后端一体化**的组织方式：

```
project-root/
├── backend/                 # Python 后端服务 (FastAPI)
│   ├── package.json          # Node.js 工具链依赖（前端构建等）
│   └── pom.xml               # Java 工具链依赖（可选）
├── frontend/                # 前端 (Vue 3 + TypeScript + Element Plus)
│   └── package.json          # 前端项目配置与依赖
├── database/                # 数据库脚本
│   ├── schema.sql            # 数据库表结构 DDL
│   └── init_data.sql         # 初始数据导入
├── docker/                  # 容器化部署
│   ├── Dockerfile            # 应用镜像构建文件
│   └── docker-compose.yml    # 多服务编排配置
└── docs/                    # 项目文档
    ├── AI_SOLUTION.md         # AI 技术方案
    ├── API.md                # API 接口文档
    ├── ARCHITECTURE.md        # 技术框架文档（本文档）
    ├── DATABASE.md            # 数据库设计文档
    └── PRD.md                # 产品需求文档
```

### 2.2 模块映射关系

```
project-root 目录            →  系统分层映射
─────────────────────────────────────────────────
backend/                    → 后端服务层 (FastAPI)
frontend/                   → 前端应用层 (Vue3)
database/                   → 数据存储层 (SQLite + Chroma)
docker/                     → 部署与运维层 (Docker + Nginx)
docs/                       → 文档知识库
```

### 2.3 目录设计原则

| 原则 | 说明 |
|------|------|
| **扁平化根目录** | backend / frontend / database / docker / docs 五大顶级目录，职责清晰 |
| **前后端分离部署** | 独立目录、独立构建、通过 Nginx 统一入口 |
| **数据库脚本独立** | schema.sql + init_data.sql 与代码解耦，支持快速重建 |
| **Docker 优先** | docker-compose.yml 一键启动全栈服务 |
| **文档即代码** | docs/ 纳入版本管理，与代码同步更新 |

---

## 三、系统总体架构

### 3.1 分层架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         前端应用层 (Vue3)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  AI智能助手   │  │  考试工坊     │  │  隐患安全管理 │              │
│  │  (SSE流式)    │  │  (AI出题)     │  │  (全生命周期)│              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │    Nginx 反向代理 + 负载均衡        │                      │
└─────────┼─────────────────┼──────────────────┼──────────────────────┘
──────────┼─────────────────┼──────────────────┼──────────────────────
          ▼                 ▼                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    后端服务层 (FastAPI)                              │
│                                                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │ AI问答服务   │  │ AI出题服务    │  │  知识库管理服务            │   │
│  │ · 意图识别   │  │ · 题型路由    │  │ · 文档上传/解析           │   │
│  │ · RAG检索    │  │ · Prompt构建  │  │ · 分块/向量化            │   │
│  │ · SSE流式输出│  │ · 答案解析    │  │ · 知识库CRUD             │   │
│  │ · 敏感词过滤 │  │ · 难度控制    │  │ · 增量更新               │   │
│  └──────┬──────┘  └──────┬───────┘  └───────────┬──────────────┘   │
│  ┌──────┴───────────────────────────────────────┴──────────────┐   │
│  │  隐患管理服务                                                  │   │
│  │  · 隐患上报/派单/整改/验收  · 统计分析  · 消息通知             │   │
│  └──────┬────────────────────────────────────────────┬─────────┘   │
│  ┌──────┴────────────────────────────────────────────┴─────────┐   │
│  │                    公共组件层                                 │   │
│  │  · 本地TTLCache  · 敏感词DFA过滤器  · 对话上下文管理  · 限流器│   │
│  │  · JWT认证      · RBAC权限校验     · 审计日志              │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────┼────────────────────────────────────────────┼─────────────┘
          │                                            │
          ▼                                            ▼
┌──────────────────────┐              ┌───────────────────────────────┐
│   数据存储层          │              │       AI能力层                 │
│                      │              │                               │
│  ┌────────────────┐  │              │  ┌─────────────────────────┐ │
│  │  SQLite        │  │              │  │  LangChain ChatModel     │ │
│  │  · 业务数据     │  │              │  │  (文心/通义/智谱 统一封装)│ │
│  │  · 题库数据     │  │              │  │  · LlmRouter 场景路由     │ │
│  │  · 审计日志     │  │              │  └───────────┬─────────────┘ │
│  └────────────────┘  │              │              │                │
│  ┌────────────────┐  │              │  ┌───────────▼─────────────┐ │
│  │  Chroma        │  │              │  │  LangChain Embeddings    │ │
│  │  · 向量索引     │  │              │  │  (HuggingFace BGE 本地) │ │
│  │  · 知识向量     │  │              │  └───────────┬─────────────┘ │
│  └────────────────┘  │              │              │                │
│                      │              │  ┌───────────▼─────────────┐ │
│                      │              │  │  LangChain Reranker      │ │
│                      │              │  │  (CrossEncoder 重排序)   │ │
│                      │              │  └─────────────────────────┘ │
└──────────────────────┘              └───────────────────────────────┘
```

### 3.2 架构设计原则

| 原则 | 说明 |
|------|------|
| **前后端分离** | Vue3 SPA + FastAPI RESTful API，通过 Nginx 反向代理统一入口 |
| **嵌入式数据层** | SQLite + Chroma 均嵌入式运行，无需独立数据库服务，降低运维复杂度 |
| **多模型协同** | 不同场景路由到最优大模型，文心一言（问答）、通义千问（出题）、智谱GLM（降级） |
| **RAG 增强检索** | 向量检索 + 关键字检索混合策略，CrossEncoder 重排序，确保回答基于知识库 |
| **RBAC 权限模型** | 管理员 / 安全员 / 普通员工三级角色，接口级 + 数据级双重权限校验 |
| **SSE 流式输出** | AI 回答实时逐字推送，降低用户等待感知 |
| **Docker 容器化** | 全栈服务容器化编排，docker-compose 一键启动 |

---

## 四、技术栈详解

### 4.1 技术栈总览

| 层级 | 技术选型 | 选型理由 |
|------|---------|---------|
| 前端 | Vue 3 + TypeScript + Element Plus | 组件化开发，TypeScript 类型安全，Element Plus 企业级组件库 |
| 后端 | FastAPI + SQLAlchemy | 高性能异步框架，原生支持 SSE，自动生成 OpenAPI 文档 |
| 业务数据库 | SQLite (WAL 模式) | 嵌入式零运维，WAL 模式提升并发读，适合中小规模并发 |
| 向量数据库 | Chroma | 嵌入式部署，HNSW 索引，百万级向量 <100ms 检索，与 SQLite 统一技术栈 |
| AI 框架 | LangChain | ChatModel 抽象统一封装多厂商大模型，内置 RAG 组件与 LCEL 链式编排 |
| 大模型 API | 文心一言 / 通义千问 / 智谱 GLM | 国内合规，中文能力强，多模型协同覆盖不同场景 |
| Embedding | bge-large-zh-v1.5 (本地部署) | 中文嵌入 C-MTEB 榜单优异，1024 维，本地 GPU 推理延迟 ~50ms |
| Reranker | bge-reranker-large (本地部署) | CrossEncoder 精排，显著提升检索准确率 |
| 部署 | Docker + Docker Compose + Nginx | 容器化部署，Nginx 反向代理 + SSE 长连接支持 |

### 4.2 大模型选型与路由策略

| 场景 | 主模型 | 备用模型 | 选型理由 |
|------|--------|---------|---------|
| AI 智能问答 | 文心一言 ERNIE-4.0-Turbo | 智谱 GLM-4 | 中文法规理解能力强，安全审核严格 |
| AI 自动出题 | 通义千问 Qwen-Plus | 文心一言 ERNIE-4.0 | 指令遵循好，JSON 结构化输出稳定 |
| 降级/高并发 | 智谱 GLM-3-Turbo | — | 性价比高，成本控制场景 |

模型路由通过 `LlmRouter` 实现：根据场景（qa / exam_generation）自动选择主模型，主模型不可用时自动降级到备用模型。

---

## 五、模块技术设计

### 5.1 隐患安全管理模块

负责隐患全生命周期管理：上报 → 派单 → 整改 → 验收 → 闭环。

| 组件 | 技术要点 |
|------|---------|
| 数据模型 | SQLAlchemy ORM，隐患表关联用户表、项目表、操作记录表 |
| 状态流转 | 状态机模式，待处理 → 处理中 → 待验收 → 已闭环 / 已驳回 |
| 文件上传 | 图片/视频上传，前端压缩 + 后端类型白名单校验 |
| 消息通知 | 站内消息表 + 轮询/SSE 推送，延迟 ≤ 5s |
| 统计分析 | ECharts 图表渲染，SQL 聚合查询，支持 Excel 导出 |
| 权限控制 | RBAC 三级角色，管理员全局 / 安全员管辖范围 / 员工本人数据 |

### 5.2 AI 智能助手模块

基于 RAG 的安全知识智能问答。

| 组件 | 技术要点 |
|------|---------|
| 意图识别 | 前置检测过滤非安全相关问题，引导聚焦安全领域 |
| 知识检索 | 混合检索（向量 + BM25）→ RRF 融合 → Top-10 → CrossEncoder 重排 → Top-5 |
| Prompt 构建 | ChatPromptTemplate 模板化，注入检索上下文 + 历史对话 + 系统指令 |
| 流式输出 | SSE (Server-Sent Events)，LangChain astream 逐 token 推送 |
| 敏感词过滤 | DFA 算法，输入前置 + 输出后置双向过滤 |
| 会话管理 | 用户维度会话列表，最近 5 轮上下文保留，上限 100 个会话 |
| 回答引用 | 角标标注 + 来源列表，可展开查看原文片段 |
| 反馈机制 | 点赞/踩 + 踩原因分类，数据用于质量分析 |

### 5.3 考试工坊模块

题库准备 → 试卷生成 → 在线考试 → 阅卷与成绩。

| 组件 | 技术要点 |
|------|---------|
| 题库管理 | SQLite 存储，支持手动录入 + Excel 批量导入，文本相似度查重 |
| AI 出题 | 基于知识库内容生成题目，支持知识点出题 / 文档出题 / 自由出题 |
| 题型支持 | 单选 / 多选 / 判断 / 填空 / 简答，严格 JSON 结构化输出 |
| 智能组卷 | 策略驱动的随机抽题（题型分布 + 难度比例 + 知识点覆盖） |
| 在线考试 | 倒计时 + 自动保存 + 切屏检测 + 断线保护 |
| 自动阅卷 | 客观题即时评分 + 简答题 AI 语义相似度评分 |
| 统计分析 | ECharts 图表 + 错题 TOP 榜 + 知识点掌握度热力图 |
| 题目审核 | 三态流转：待审核 → 已发布 / 已驳回，编辑后通过保留修改记录 |

---

## 六、AI 与 RAG 架构

### 6.1 RAG 完整流程

```
═══════════════ 离线知识库构建 ════════════════

文档收集 → 格式转换(PDF/Word/MD→文本) → 内容清洗 → 元数据标注
                                                       ↓
                                              文本分块(递归字符分割)
                                              chunk_size=500, overlap=100
                                                       ↓
                                              向量化(bge-large-zh-v1.5)
                                                       ↓
                                              存入 Chroma(HNSW 索引)

═══════════════ 在线问答检索 ════════════════

用户提问 → 敏感词检测(DFA) → 意图识别(是否安全相关?)
                                        ↓ (是)
                              查询向量化 → 混合检索(向量+BM25,Top-10)
                                        → RRF 融合排序
                                        → CrossEncoder 重排序(Top-5)
                                        → Prompt 构建(注入上下文+历史)
                                        → 大模型生成(SSE流式)
                                        → 敏感词后置过滤
                                        → 返回回答(含引用来源)
```

### 6.2 关键组件

| 组件 | 技术方案 | 关键参数 |
|------|---------|---------|
| 文档加载 | LangChain DocumentLoader | 支持 PDF / DOCX / TXT / MD |
| 文本分块 | RecursiveCharacterTextSplitter | chunk_size=500, chunk_overlap=100 |
| 向量化 | HuggingFaceEmbeddings (bge-large-zh-v1.5) | 维度=1024, 本地 GPU/CPU |
| 向量检索 | Chroma HNSW 索引 | 余弦相似度, Top-K=10 |
| 混合检索 | 向量检索 + BM25 关键字检索 | RRF 融合 (k=60) |
| 重排序 | CrossEncoder (bge-reranker-large) | 阈值=0.3, 精排至 Top-5 |
| 流式输出 | LangChain astream + SSE | 首 Token ~1-2s |

### 6.3 知识库内容体系

```
蜀道安全知识库
├── 国家法律法规（安全生产法、建筑法、消防法、职业病防治法等）
├── 行业标准规范（JTG F90 公路工程施工安全规范等）
├── 企业内部制度（安全管理办法、责任制度、检查制度等）
├── 安全操作规程（高处作业、动火作业、临时用电、起重吊装等）
├── 应急预案（综合/专项应急预案、现场处置方案）
└── 事故案例分析（坍塌、高处坠落、机械伤害、触电、火灾爆炸等）
```

### 6.4 RAG 优化路径

#### 6.4.1 优化路线总览

基于 RAG 基线（固定窗口分块 + 纯稠密向量检索）的已知局限性，制定分阶段、数据驱动的五阶段优化路线：

```
P0 基线 ──→ P1 分块治理 ──→ P2 混合检索 ──→ P3 精排+改写 ──→ P4 领域深化(可选)

跑通流程    不切坏语义     术语也能命中    答案更准        知识图谱+微调+闭环
```

| 阶段 | 目标 | 关键动作 | 验证指标 | 技术栈增量 |
|------|------|---------|---------|-----------|
| P0 基线 | 跑通可用 RAG | 固定窗口分块 + 稠密检索 Top-4 | 端到端能答 | RecursiveCharacterTextSplitter + Chroma |
| P1 分块治理 | 不切坏语义 | 结构感知分块 + 父子块 + bge-m3 评估 | Recall@4 ≥ 0.7 | MarkdownHeaderTextSplitter + ParentDocumentRetriever |
| P2 混合检索 | 术语也能命中 | 稠密+稀疏 RRF + 元数据过滤 | Recall@10 ≥ 0.85 | BM25Retriever + RRF 融合 + metadata filter |
| P3 精排+改写 | 答案更准 | Reranker 重排 + 查询改写/HyDE | 人工评分 ≥ 4/5 | CrossEncoder(bge-reranker) + HyDE |
| P4 进阶(可选) | 领域深化 | 事故案例知识图谱 + 嵌入微调 + A07 反馈闭环 | 持续迭代 | Neo4j/NetworkX + LoRA 微调 |

#### 6.4.2 P1 分块治理

```python
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain.retrievers import ParentDocumentRetriever

headers_to_split_on = [
    ("#", "h1"), ("##", "h2"), ("###", "h3"),
]
splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=headers_to_split_on, strip_headers=False
)

retriever = ParentDocumentRetriever(
    vectorstore=Chroma(embedding_function=embeddings),
    docstore=InMemoryStore(),
    child_splitter=RecursiveCharacterTextSplitter(chunk_size=300, overlap=50),
    parent_splitter=RecursiveCharacterTextSplitter(chunk_size=1000, overlap=100),
    search_kwargs={"k": 4}
)
```

#### 6.4.3 P2 混合检索

```python
filter_dict = {
    "$and": [
        {"doc_type": {"$in": ["REGULATION", "STANDARD"]}},
        {"scope": "高处作业"}
    ]
}
results = vector_store.similarity_search(query, k=10, filter=filter_dict)
```

#### 6.4.4 评估体系

| 指标 | 定义 | 适用阶段 | 达标标准 |
|------|------|---------|---------|
| Recall@K | Top-K 结果中包含相关文档的比例 | P1-P4 | P1:@4≥0.7; P2:@10≥0.85 |
| Precision@K | Top-K 结果中相关文档的比例 | P2-P4 | 辅助参考 |
| MRR | 第一个相关文档排名的倒数均值 | P2-P4 | 辅助参考 |
| 人工评分 | 对生成答案的 1-5 分评分 | P3-P4 | ≥ 4.0/5 |
| 用户满意度 | 点赞率（A07 反馈） | P3-P4 | 趋势上升 |

---

## 七、数据架构设计

### 7.1 数据库分层

业务库与知识库分离：ackend/data/app.db 承担用户/隐患/考试等可写业务；database/transport-safety-kb/data/transport_safety_kb.sqlite3 只读提供正式依据检索。

```
┌─────────────────────────────────────────┐
│              数据存储层                  │
│                                         │
│  SQLite (业务数据)                       │
│  ├── 用户表 (user)                      │
│  ├── 角色表 (role)                      │
│  ├── 隐患表 (hazard)                    │
│  ├── 隐患操作记录表 (hazard_log)         │
│  ├── 题库表 (question)                  │
│  ├── 试卷表 (exam_paper)                │
│  ├── 考试记录表 (exam_record)           │
│  ├── 会话表 (conversation)             │
│  ├── 消息表 (message)                   │
│  ├── 知识文档表 (knowledge_document)    │
│  └── AI 审计日志表 (ai_audit_log)       │
│                                         │
│  Chroma (向量数据)                       │
│  └── safety_knowledge (知识向量集合)     │
│      ├── 向量索引 (HNSW)                │
│      └── 元数据 (document_id/type/name) │
└─────────────────────────────────────────┘
```

### 7.2 核心数据模型关系

- **用户-角色**：多对一，三级 RBAC 角色
- **隐患-用户**：上报人、责任人、验收人多维度关联
- **隐患-操作记录**：一对多，完整状态流转时间线
- **题目-知识分类**：多对多，支持多级分类树
- **试卷-题目**：多对多，组卷灵活配置
- **会话-消息**：一对多，多轮对话上下文

---

## 八、安全架构

### 8.1 安全三道防线

```
第一道: 输入预处理
├── 敏感词 DFA 过滤
├── 意图安全检测（是否涉及违规话题）
└── Prompt 注入防护（恶意指令检测）

第二道: 大模型内置审核
├── 模型自带内容安全策略
└── System Prompt 安全约束

第三道: 输出后处理
├── 敏感词二次过滤
├── 安全合规校验
└── 审计日志记录
```

### 8.2 敏感词 DFA 过滤器

```python
"""
敏感词过滤服务
采用 DFA（确定有限自动机）算法，高性能匹配
"""
from dataclasses import dataclass, field


@dataclass
class MatchResult:
    """敏感词匹配结果"""
    word: str
    start: int
    end: int
    category: str = ""


@dataclass
class FilterResult:
    """过滤结果"""
    passed: bool = True
    reason: str = ""
    filtered_content: str = ""
    matches: list[MatchResult] = field(default_factory=list)

    @classmethod
    def ok(cls) -> "FilterResult":
        return cls(passed=True)


class DFAFilter:
    """DFA 敏感词匹配引擎"""

    def __init__(self):
        self._trie: dict = {}

    def add_word(self, word: str, category: str = "") -> None:
        node = self._trie
        for char in word:
            node = node.setdefault(char, {})
        node["__end__"] = True
        node["__word__"] = word
        node["__category__"] = category

    def load_words(self, words: list[str], category: str = "") -> None:
        for w in words:
            self.add_word(w, category)

    def match(self, text: str) -> list[MatchResult]:
        results: list[MatchResult] = []
        n = len(text)
        for i in range(n):
            node = self._trie
            j = i
            while j < n and text[j] in node:
                node = node[text[j]]
                j += 1
                if node.get("__end__"):
                    results.append(MatchResult(
                        word=node["__word__"],
                        start=i, end=j,
                        category=node.get("__category__", ""),
                    ))
        return results

    def replace(self, text: str, mask: str = "***") -> str:
        matches = self.match(text)
        if not matches:
            return text
        result = list(text)
        for m in reversed(matches):
            result[m.start:m.end] = list(mask)
        return "".join(result)


class SensitiveWordFilter:
    """敏感词过滤服务（输入前置 + 输出后置）"""

    BLOCKED_CATEGORIES = {
        "政治敏感", "暴力恐怖", "色情低俗", "违法犯罪",
        "广告引流", "个人隐私", "其他违规",
    }

    def __init__(self):
        self.dfa_filter = DFAFilter()

    def filter_input(self, text: str) -> FilterResult:
        matches = self.dfa_filter.match(text)
        if matches:
            return FilterResult(
                passed=False,
                reason="输入包含敏感内容，请修改后重试",
                matches=matches,
            )
        return FilterResult.ok()

    def filter_output(self, text: str) -> FilterResult:
        matches = self.dfa_filter.match(text)
        if matches:
            filtered = self.dfa_filter.replace(text, "***")
            return FilterResult(
                passed=True,
                filtered_content=filtered,
                matches=matches,
            )
        return FilterResult.ok()
```

### 8.3 审计日志 ORM 模型

```python
"""
AI对话审计日志
SQLAlchemy ORM 模型，映射 ai_audit_log 表
"""
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Text, DateTime, JSON
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class AiAuditLog(Base):
    """AI对话审计日志"""

    __tablename__ = "ai_audit_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String(64), index=True, comment="会话ID")
    user_id = Column(String(64), index=True, comment="用户ID")
    user_question = Column(Text, comment="用户提问")
    ai_answer = Column(Text, comment="AI回答")
    model_used = Column(String(128), comment="使用的模型")
    response_time = Column(BigInteger, comment="响应时间(ms)")
    sources = Column(JSON, comment="引用来源")
    filter_action = Column(String(64), comment="过滤动作")
    create_time = Column(
        DateTime, default=datetime.now, comment="创建时间"
    )
```

### 8.4 安全措施清单

| 安全域 | 措施 |
|--------|------|
| 身份认证 | JWT Token（有效期 2h，支持刷新），BCrypt 密码加盐 |
| 权限控制 | RBAC 模型，接口级 + 数据级双重校验 |
| 传输安全 | 全站 HTTPS (TLS 1.2+)，CSP 内容安全策略 |
| 数据安全 | SQLAlchemy 参数化查询防注入，敏感字段脱敏，文件类型白名单 |
| AI 安全 | 双向敏感词 DFA 过滤，Prompt 注入防护，单用户限流 ≤ 10 次/分钟 |
| 审计追溯 | AI 对话全量审计日志（会话 ID / 用户 / 问题 / 回答 / 模型 / 耗时 / 引用来源） |

---

## 九、部署架构

### 9.1 Docker 部署架构图

```
┌─────────────────────────────────────────────────────────┐
│                   Docker Compose 部署架构                 │
│                                                         │
│  ┌──────────┐  ┌──────────┐                             │
│  │  Nginx   │  │ Vue3前端  │                             │
│  │  :80/:443│──│ 静态资源  │                             │
│  └────┬─────┘  └──────────┘                             │
│       │                                                  │
│       ▼                                                  │
│  ┌──────────┐  ┌──────────┐                             │
│  │ FastAPI  │  │ FastAPI  │   ← 多 worker 进程           │
│  │  #1       │  │  #2       │    (uvicorn workers=4)     │
│  │ :8081    │  │ :8082    │                             │
│  └──────────┘  └──────────┘                             │
│                                                         │
│  注：SQLite 和 Chroma 作为嵌入式组件，直接运行在         │
│  FastAPI 进程中，无需独立服务容器。                       │
│                                                         │
│  ┌──────────────────────┐                               │
│  │  BGE模型服务          │  (GPU 容器)                   │
│  │  bge-large-zh +      │                               │
│  │  bge-reranker        │                               │
│  │  :8088               │                               │
│  └──────────────────────┘                               │
└─────────────────────────────────────────────────────────┘
```

### 9.2 docker-compose.yml

```yaml
version: '3.8'
services:
  nginx:
    image: nginx:latest
    ports: ["80:80", "443:443"]
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./frontend/dist:/usr/share/nginx/html
    depends_on: [app-1, app-2]

  app-1:
    image: shudao-safety-assistant:latest
    ports: ["8081:8080"]
    environment:
      - APP_ENV=prod
      - UVICORN_PORT=8080
      - CHROMA_PERSIST_DIR=/data/chroma
      - SQLITE_PATH=/data/safety_assistant.db
    volumes:
      - app_data:/data
    depends_on: [embedding-service]

  app-2:
    image: shudao-safety-assistant:latest
    ports: ["8082:8080"]
    environment:
      - APP_ENV=prod
      - UVICORN_PORT=8080
      - CHROMA_PERSIST_DIR=/data/chroma
      - SQLITE_PATH=/data/safety_assistant.db
    volumes:
      - app_data:/data
    depends_on: [embedding-service]

  embedding-service:
    image: bge-embedding:latest
    ports: ["8088:8088"]
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]

volumes:
  app_data:
```

### 9.3 Nginx SSE 流式配置

```nginx
# SSE 流式接口特殊配置
location /api/ai/chat/stream {
    proxy_pass http://backend;

    # SSE 关键配置
    proxy_buffering off;            # 关闭缓冲，实时推送
    proxy_cache off;                # 关闭缓存
    proxy_set_header Connection ''; # 清除 Connection 头
    proxy_http_version 1.1;         # HTTP/1.1 支持长连接
    chunked_transfer_encoding on;   # 分块传输

    # 超时配置
    proxy_read_timeout 300s;        # SSE 长连接超时
    proxy_send_timeout 300s;
}

# 普通 API 负载均衡
location /api/ {
    proxy_pass http://backend;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}

upstream backend {
    server app-1:8080 weight=1;
    server app-2:8080 weight=1;
    keepalive 32;
}
```

---

## 十、性能策略

### 10.1 性能优化总览

```
目标: 首字响应 ≤3s、并发 ≥50 QPS

┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  缓存策略      │  │  并发处理      │  │  流式输出      │
│ · 热点问答缓存 │  │ · 线程池调优   │  │ · SSE首字优化 │
│ · Embedding缓存│  │ · 异步非阻塞   │  │ · 分块传输    │
│ · 检索结果缓存 │  │ · 限流降级    │  │ · 背压控制    │
└──────────────┘  └──────────────┘  └──────────────┘
```

### 10.2 缓存服务实现

基于 `cachetools` 本地 TTLCache，纯 Python 实现，无需 Redis：

```python
"""
本地缓存服务
基于 cachetools TTLCache 实现纯本地缓存
"""
import hashlib
from cachetools import TTLCache

QA_CACHE_PREFIX = "qa:"
EMBEDDING_CACHE_PREFIX = "emb:"


class CacheService:
    """纯本地缓存：基于 cachetools TTLCache"""

    def __init__(self):
        self.qa_cache: TTLCache = TTLCache(
            maxsize=1000, ttl=1800,      # 问答缓存：1000条，30分钟
        )
        self.emb_cache: TTLCache = TTLCache(
            maxsize=5000, ttl=86400,     # Embedding缓存：5000条，24小时
        )

    @staticmethod
    def _md5(text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    def get_cached_answer(self, question: str) -> str | None:
        cache_key = QA_CACHE_PREFIX + self._md5(question.strip().lower())
        return self.qa_cache.get(cache_key)

    def cache_answer(self, question: str, answer: str) -> None:
        cache_key = QA_CACHE_PREFIX + self._md5(question.strip().lower())
        self.qa_cache[cache_key] = answer

    def get_cached_embedding(self, text: str) -> list[float] | None:
        key = EMBEDDING_CACHE_PREFIX + self._md5(text)
        return self.emb_cache.get(key)

    def cache_embedding(self, text: str, vector: list[float]) -> None:
        key = EMBEDDING_CACHE_PREFIX + self._md5(text)
        self.emb_cache[key] = vector
```

### 10.3 缓存命中场景

| 缓存层 | 缓存对象 | Key策略 | TTL | 适用场景 |
|--------|---------|---------|-----|---------|
| 本地 TTLCache | 高频问答结果 | MD5(问题文本) | 30min | 重复提问，毫秒级返回 |
| 本地 TTLCache | Embedding 向量 | MD5(文本内容) | 24h | 避免重复调用 Embedding |
| 本地 TTLCache | 检索结果 | MD5(查询词) | 10min | 避免重复向量检索 |

### 10.4 并发控制与限流

```python
"""
限流与降级服务
基于本地内存实现滑动窗口限流
"""
import time
from collections import defaultdict


class RateLimitService:
    """本地内存限流"""

    def __init__(self):
        self._counters: dict[str, list[float]] = defaultdict(list)

    def allow_request(self, user_id: str, max_qps: int) -> bool:
        now = time.time()
        window_start = now - 1.0

        self._counters[user_id] = [
            t for t in self._counters[user_id] if t > window_start
        ]

        if len(self._counters[user_id]) >= max_qps:
            return False

        self._counters[user_id].append(now)
        return True
```

### 10.5 SSE 流式端点实现

```python
"""
SSE流式输出 - FastAPI StreamingResponse + LangChain astream
"""
import json
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/chat/stream")
async def chat_stream(
    question: str = Query(..., description="用户提问"),
    session_id: str = Query(..., description="会话ID"),
):
    """SSE 流式问答接口"""

    async def event_generator():
        try:
            async for chunk in rag_orchestrator.rag_answer_stream(
                session_id, question
            ):
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Nginx 关闭缓冲
        },
    )
```

### 10.6 性能指标达成路径

```
首字响应 ≤3s 达成路径:
  Embedding 缓存命中 (~10ms)
  + Chroma HNSW 检索 (~200ms)
  + BGE Rerank (~100ms)
  + Prompt 构建 (~10ms)
  + 大模型首 Token (~1-2s)
  = 总计 ~1.3-2.3s ✅

并发 ≥50 QPS 达成路径:
  uvicorn 多 worker 异步并发
  + 本地缓存命中率 30%+（减少 30% 大模型调用）
  + 异步非阻塞 SSE（不占用线程）
  + 模型 API QPS 提升申请
  = 有效并发 ~60-80 QPS ✅
```

| 指标 | 目标值 | 优化措施 | 预估达成 |
|------|--------|---------|---------|
| 首字响应时间 | ≤3s | Embedding缓存+Chroma HNSW+SSE流式 | ~1.5-2.5s ✅ |
| 并发 QPS | ≥50 | uvicorn多worker+本地缓存+异步非阻塞 | ~60-80 ✅ |
| 缓存命中率 | ≥30% | 本地TTLCache+热点预热 | ~35-45% ✅ |
| 检索延迟 | ≤500ms | HNSW索引+混合检索并行 | ~200-400ms ✅ |
| Embedding 延迟 | ≤100ms | 本地BGE模型+缓存 | ~30-80ms ✅ |

---

## 十一、核心技术决策总结

| 决策项 | 选型 | 核心理由 |
|--------|------|---------|
| 问答大模型 | 文心一言 ERNIE-4.0-Turbo | 中文法规理解最强 |
| 出题大模型 | 通义千问 Qwen-Plus | 结构化输出稳定 |
| Embedding 模型 | bge-large-zh-v1.5 | 中文嵌入效果优、本地部署低延迟 |
| 向量数据库 | Chroma | 嵌入式部署、与 SQLite 统一技术栈、零运维 |
| 重排序模型 | bge-reranker-large | CrossEncoder 精排提升检索准确率 |
| 流式输出 | SSE | 兼容性好、Nginx 配置简单 |
| 缓存方案 | cachetools 本地 TTLCache | 轻量级、无需外部服务 |
| 业务数据库 | SQLite (WAL 模式) | 嵌入式零运维、满足中小规模并发 |
| AI 框架 | LangChain | ChatModel 统一封装、RAG 组件成熟 |
| 部署方案 | Docker Compose | 容器化管理、一键部署 |

---

*— 文档结束 —*
*（内容由AI生成，仅供参考）*
