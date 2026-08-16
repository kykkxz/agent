# 蜀道安全助手

面向蜀道集团安全生产管理的 AI 平台，覆盖隐患闭环、知识库问答和考试工坊。

## 架构分层

- `backend/` FastAPI 业务服务（用户、隐患、考试、通知、统计）
- `frontend/` Vue 3 指挥台
- `database/transport-safety-kb/` 已落地的交通安全知识库（SQLite + Chroma）
- `docs/` PRD / API / 架构 / AI 方案
- `docker/` 一键编排

业务库与知识库分离：业务写入 `backend/data/app.db`，问答只读检索 `transport_safety_kb.sqlite3`。未配置大模型时，助手会基于检索证据生成可引用回答。

当前可运行能力、真实路由与规划边界以 [`docs/CURRENT_IMPLEMENTATION.md`](docs/CURRENT_IMPLEMENTATION.md) 为准。现有 PRD、架构与 AI 方案包含后续目标设计，不应全部视为已实现。

## 本地启动

```powershell
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

```powershell
cd frontend
npm install
npm run dev
```

打开 [http://127.0.0.1:5173](http://127.0.0.1:5173)

演示账号：

| 用户 | 密码 | 角色 |
| --- | --- | --- |
| admin | Admin@123456 | 管理员 |
| safety | Safety@123456 | 安全员 |
| worker | Worker@123456 | 一线员工 |

## 隐患图片批注命令

后端 API 与命令行工具复用相同的视觉模型配置、提示词和批注算法：

```powershell
cd backend
python scripts/annotate_hazards.py --image <图片路径>
```

使用 `--annotations <标注.json>` 可跳过视觉模型调用，仅重新绘制已有批注。

## 接口与文档

- API 前缀：`/api/v1`
- 交互文档：`http://127.0.0.1:8000/docs`
- 需求与接口说明见 `docs/PRD.md`、`docs/API.md`、`docs/ARCHITECTURE.md`
- 当前实现基线见 `docs/CURRENT_IMPLEMENTATION.md`

## 测试

```powershell
cd backend
python -m pytest -q
```
