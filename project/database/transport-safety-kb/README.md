# 交通建设与运营安全数据采集插件

本项目依据《交通建设与运营安全_第一轮数据采集插件规划》实现。首轮已覆盖法规、监管文件、事故材料、企业制度、操作规程、应急预案和来源治理。

## 运行

使用系统全局 Python，不需要创建虚拟环境：

```powershell
python query_database.py
python run_pipeline.py
python run_pipeline.py --offline
python migrate_database.py
python tools/discover_official_catalog.py --source mem --timeout 12
python tools/discover_official_catalog.py --source hcq --timeout 12
python tools/discover_official_catalog.py --source huli --timeout 12
python tools/discover_official_catalog.py --finalize-only
python -m transport_kb.cli collect --manifest config/sources.json --output data
python -m transport_kb.cli status --output data
python -m transport_kb.cli search --output data --query "安全生产责任由谁承担"
python -m transport_kb.cli evaluate --output data --questions config/acceptance_questions.json
python query_database.py tables
python query_database.py schema --table documents
python query_database.py rows --table documents --limit 10
python query_database.py rows --table documents --where "document_type=法律"
python query_database.py search --keyword "隧道事故"
python -m unittest discover -s tests -v
```

直接运行 `query_database.py` 会启动 Rich 中文交互界面，可从菜单浏览表、分页查看记录、
打开单条详情、按关键词跨表搜索以及精确筛选。脚本以只读方式打开 SQLite。`tables` 列出业务表及记录数，`schema`
查看字段结构，`rows` 分页浏览并支持重复使用 `--where 字段=值` 精确筛选，`search`
可跨全部业务表或通过 `--table` 限定单表搜索。全局参数 `--database` 可指定其他
SQLite 文件，`--json` 可输出结构化结果；全局参数需放在子命令之前。

`run_pipeline.py` 是固定闭环入口，依次完成配置与本地原件校验、采集、原档归档、
正文抽取、来源治理、去重与版本处理、证据和知识条目生成、SQLite 重建、固定问题验收、
数据库完整性检查及最终报告。`--offline` 仅处理本地 PDF，不访问网络。

已完成政府来源校验后，可运行 `python -X utf8 mark_gov_validated.py`，将 `gov.cn` 及其子域来源对应的文档和知识条目标记为“通过校验/正式依据层”，并同步更新 JSONL 导出和报告。脚本会先创建带时间戳的备份，其他来源保持原审核状态。

事故目录发现脚本按站点分批运行，使用 `data/discovery_checkpoints/*.jsonl` 即时保存
检查点；重复运行会跳过未变化记录，单个索引失败会写入独立失败清单。目录汇总后，
`run_pipeline.py` 负责正文和附件原档归档、旧版 DOC 提取、多文档附件拆分及 SQLite 重建。

当前首轮在线闭环包含 62 起官方事故报告、21 份应急预案、10 个高风险操作规程、
21 份企业制度（覆盖 20 个具名企业/项目/工区），所有结果仍标记为机器初审/待核验层。

在线模式通过 Windows `curl.exe` 获取配置中的公开官方网页和附件，以使用系统证书存储。
插件不会绕过登录、验证码或访问控制。浏览器核验结果记录在来源配置和每份原档的元数据中。


## RAG 向量库（正式依据层）

仅对“通过校验 / 正式依据层”证据单元建立语义索引，事实源仍是 SQLite。注意：Windows 下 Chroma/HNSW 无法在含中文的路径中正确落盘索引。构建脚本会自动改写为 8.3 短路径（或 `H:/wd/tskb-artifacts` 回退），并在逻辑目录写入 `CHROMA_PATH.txt` 指向真实索引位置。

本地模型目录默认：

- 嵌入：`../bge-small-zh-v1.5`
- 重排：`../bge-reranker-base`

构建与验收：

```powershell
python tools/build_rag_vector_store.py --reset --device cuda
python tools/test_rag_retrieval.py --device cuda
python -m unittest tests.test_rag_retrieval -v
```

输出：

- `data/rag_chroma/`：Chroma 持久化向量库与 `manifest.json`
- `data/reports/rag_vector_store_report.json`：建库报告
- `data/reports/rag_retrieval_report.json`：混合检索验收报告

依赖（可选 extra）：

```powershell
pip install -e ".[rag]"
```

## 输出

- `data/source_archive/`：按来源和 SHA-256 保存 PDF、DOCX、HTML 等原档及采集元数据
- `data/raw_manifest.jsonl`：原档索引和哈希清单
- `data/documents.jsonl`：标准文档
- `data/evidence.jsonl`：可引用证据单元
- `data/knowledge_base.jsonl`：首轮知识条目
- `data/quarantine.jsonl`：被治理规则隔离的文档
- `data/transport_safety_kb.sqlite3`：首轮知识库正式 SQLite 文件
- `data/rag_chroma/`：正式依据层 RAG 向量库（Chroma）
- `data/reports/`：运行、质量、失败、来源登记和检索验收报告

SQLite 使用外键约束和事务化重建；临时数据库通过 `integrity_check` 与
`foreign_key_check` 后才替换正式文件。当前环境支持 FTS5，并同步建立全文检索表。

SQLite 模式 v2 保留独立的 `knowledge_entries` 知识层，但去掉证据和引用表中可由外键
推导的来源、标题、审核等重复字段；`documents.raw_asset_id` 直接连接原始归档，避免通过
`source_id + raw_path` 间接追溯。已有 v1 数据库可使用 `python migrate_database.py` 迁移。

机器采集结果统一标记为“机器初审/待核验层”。未经过人工审核的内容不会标记为正式依据层。
