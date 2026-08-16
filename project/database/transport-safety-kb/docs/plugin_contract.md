# 采集插件接口约定

每个插件实现 `discover()` 和 `fetch()`；统一管线负责 `extract()`、`normalize()` 和 `emit()`。

- `discover(config) -> list[SourceCandidate]`：发现新增或更新文档。
- `fetch(candidate) -> FetchResult`：获取公开网页、附件或公开 API 响应。
- 单个来源失败只进入失败清单，不中断其他插件。
- 来源特有字段保存在 `SourceCandidate.extra`，不暴露给治理后的标准数据。
- 每轮采集生成唯一 `task_id`，原始响应按 SHA-256 只读留存。

新增插件时继承 `SourcePlugin` 并在 `CollectionPipeline.plugins` 注册，不需要修改治理、证据或知识层。

