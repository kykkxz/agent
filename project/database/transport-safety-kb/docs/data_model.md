# 数据模型与字段规范

## 原始资料

记录任务编号、原始/最终 URL、采集时间、HTTP 状态、媒体类型、传输方式、文件 SHA-256 和相对路径。

## 标准文档

覆盖任务书要求的 `document_id`、`source_id`、`raw_asset_id`、标题、文档类型、发布日期、生效区间、版本状态、管辖范围、适用角色/活动、许可状态、正文指纹、采集时间、原文定位和审核状态；来源 URI、发布机构和权威等级通过来源关联获取。

## 证据单元

法规优先按“第X条”切分；其他正文按段落窗口切分。每个单元保留文档 ID、条款/段落定位、正文和哈希；来源信息通过文档关联获取。

## 知识条目

包含主题、风险类别、内容摘要、引用列表、审核状态、发布层、失效状态和原文档 ID；文档类型、版本、适用对象、来源等级等属性通过文档关联获取。
# SQLite 持久化

首轮正式库为 `data/transport_safety_kb.sqlite3`，模式版本为 2。主要表包括：

- `collection_runs`、`sources`、`raw_assets`
- `documents`、`document_relations`
- `evidence_units`、`knowledge_entries`、`knowledge_citations`
- `quarantine`、`collection_failures`
- `knowledge_fts`（FTS5 可用时为全文索引，否则使用普通表回退）

每个 `raw_assets` 记录同时指向原档文件和 `.metadata.json`，确保结构化知识可追溯到
未改写的 PDF、DOCX 或 HTML 原始字节。

`knowledge_entries` 保留为独立知识层，但只保存主题、结论、风险分类、审核和发布状态；
文档类型、版本、适用角色等文档属性通过 `document_id` 获取。证据和引用表不再复制
来源 URI、标题、权威等级等父表字段。

完整的字段字典、实体关系、外键、索引和当前数据快照见
[`database_schema.md`](database_schema.md)。
