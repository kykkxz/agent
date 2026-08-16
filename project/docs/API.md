---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 619a68374c198f2d1dccd9a31deded68_67b21356961b11f181ac525400f8a581
    ReservedCode1: 2Z6/+YkMOF4njb/ZtsisP6ovf+U8LJ0ocDOmYszCwEQpWfNe63kUMrewt8NzSXydGJfh9aiwMAotlhm8kzTfBCPHVueem+Y2EsfJtoe3XX4Z14ygqxJO30/aVi8hVF3pNB7oprgFq2xZdgcG2DQM1pUzfZ3Oncw7GZ3QMFEbheD4q8+iIqyF/L9fk0Y=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 619a68374c198f2d1dccd9a31deded68_67b21356961b11f181ac525400f8a581
    ReservedCode2: 2Z6/+YkMOF4njb/ZtsisP6ovf+U8LJ0ocDOmYszCwEQpWfNe63kUMrewt8NzSXydGJfh9aiwMAotlhm8kzTfBCPHVueem+Y2EsfJtoe3XX4Z14ygqxJO30/aVi8hVF3pNB7oprgFq2xZdgcG2DQM1pUzfZ3Oncw7GZ3QMFEbheD4q8+iIqyF/L9fk0Y=
---

# 蜀道安全助手 — API 接口文档

> **文档状态说明（2026-08-14）**：本文保留接口目标设计。当前已实现路由、请求字段和返回结构以 [CURRENT_IMPLEMENTATION.md](./CURRENT_IMPLEMENTATION.md) 与后端 `backend/app/routers/` 为准；未在后端路由中出现的接口属于规划项。

> **项目名称**：蜀道安全助手  
> **文档版本 | V1.1  
> **编写日期**：2026-08-12  
> **基础路径**：`http://{host}:{port}/api/v1`  
> **内容格式**：`application/json`（除文件上传使用 `multipart/form-data`、SSE 流使用 `text/event-stream`外）  
> **认证方式**：Bearer Token（JWT），Header: `Authorization: Bearer <token>`

---

## 目录

- [1. 通用规范](#1-通用规范)
- [2. 认证与用户管理](#2-认证与用户管理)
- [3. 隐患安全管理](#3-隐患安全管理)
- [4. AI 智能助手](#4-ai-智能助手)
- [5. 考试工坊](#5-考试工坊)
- [6. 消息通知](#6-消息通知)
- [7. 统计分析](#7-统计分析)
- [8. 知识库管理](#8-知识库管理)
- [附录：错误码参考](#附录错误码参考)

---

## 1. 通用规范

### 1.1 请求格式

| 场景 | Content-Type |
|------|-------------|
| JSON 请求体 | `application/json` |
| 文件上传 | `multipart/form-data` |
| SSE 流式 | 客户端 Accept: `text/event-stream` |

### 1.2 统一响应结构

```json
{
  "code": 0,
  "message": "success",
  "data": {},
  "timestamp": 1692000000
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | int | 业务状态码，0 表示成功，非 0 为错误 |
| `message` | string | 状态描述 |
| `data` | object / array / null | 响应数据 |
| `timestamp` | int | 响应时间戳（Unix 秒） |

### 1.3 分页请求参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | 1 | 页码（从 1 开始） |
| `page_size` | int | 20 | 每页条数（可选 10/20/50） |

### 1.4 分页响应结构

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [],
    "total": 150,
    "page": 1,
    "page_size": 20,
    "total_pages": 8
  }
}
```

### 1.5 权限标识

接口标注所需角色：`Admin`（管理员）、`SafetyOfficer`（安全员）、`Employee`（普通员工）。未标注即所有已认证用户均可访问。

### 1.6 认证要求

除登录接口外，所有接口均需在 Header 中携带 JWT Token：

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

Token 有效期 2 小时，过期后需通过刷新接口续期。30 分钟无操作自动登出。

---

## 2. 认证与用户管理

### 2.1 登录

```
POST /auth/login
```

**请求体**：

```json
{
  "username": "zhangsan",
  "password": "Abc@123456"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `username` | string | 是 | 用户名或工号 |
| `password` | string | 是 | 密码（≥ 8 位，含大小写字母+数字+特殊字符） |

**成功响应**：

```json
{
  "code": 0,
  "data": {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "expires_in": 7200,
    "user": {
      "id": "U001",
      "username": "zhangsan",
      "name": "张三",
      "role": "SafetyOfficer",
      "department": "安全生产部",
      "project": "成绵高速扩容项目"
    }
  }
}
```

**错误码**：`40101` 用户名或密码错误、`40102` 账户已被禁用

---

### 2.2 刷新 Token

```
POST /auth/refresh
```

**请求体**：

```json
{
  "refresh_token": "eyJhbGciOi..."
}
```

**成功响应**：同 2.1 登录响应结构。

**错误码**：`40103` refresh_token 无效或已过期

---

### 2.3 退出登录

```
POST /auth/logout
```

**请求体**：无

**成功响应**：`{ "code": 0, "message": "已退出登录" }`

---

### 2.4 获取当前用户信息

```
GET /auth/me
```

**响应**：同 2.1 中 `user` 字段。

---

### 2.5 修改密码

```
PUT /auth/password
```

**请求体**：

```json
{
  "old_password": "Abc@123456",
  "new_password": "Xyz@654321"
}
```

**成功响应**：`{ "code": 0, "message": "密码修改成功" }`

**错误码**：`40104` 旧密码错误、`40001` 新密码不符合复杂度要求

---

### 2.6 用户列表（管理员）

```
GET /users
```

> **角色**：Admin

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `page` | int | 否 | 页码 |
| `page_size` | int | 否 | 每页条数 |
| `keyword` | string | 否 | 用户名/姓名搜索 |
| `role` | string | 否 | 按角色筛选（SafetyOfficer / Employee） |
| `department` | string | 否 | 按部门筛选 |

**响应数据**：分页格式，`items` 为 `user` 对象数组（同 2.1 user 结构，不含 token）。

---

### 2.7 创建/编辑/删除用户（管理员）

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/users` | 创建用户 |
| `PUT` | `/users/{user_id}` | 编辑用户信息 |
| `DELETE` | `/users/{user_id}` | 删除用户（软删除） |

> **角色**：Admin

**创建/编辑请求体**：

```json
{
  "username": "lisi",
  "name": "李四",
  "password": "Xyz@654321",
  "role": "Employee",
  "department": "工程部",
  "project": "绵九高速项目",
  "phone": "13800138000"
}
```

---

## 3. 隐患安全管理

### 3.1 隐患上报

```
POST /hazards
```

> **角色**：Admin / SafetyOfficer / Employee  
> **对应功能**：H01

**请求体**（`multipart/form-data`）：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | 是 | 隐患标题（≤ 100 字） |
| `description` | string | 是 | 详细描述（≤ 2000 字） |
| `level` | string | 是 | 隐患等级：`critical`（重大）/ `major`（较大）/ `minor`（一般）/ `trivial`（轻微） |
| `category` | string | 是 | 隐患类别：`height_work` / `edge_protection` / `machinery` / `fire_safety` / `temp_electricity` 等 |
| `location` | string | 是 | 发生位置描述 |
| `location_coords` | string | 否 | GPS 坐标（`"lng,lat"` 格式） |
| `occurred_at` | string | 是 | 发生时间（ISO 8601） |
| `project` | string | 是 | 所属项目/标段 |
| `images` | file[] | 否 | 现场照片（最多 9 张，单张 ≤ 10MB） |
| `videos` | file[] | 否 | 现场视频（最多 3 段，单段 ≤ 50MB） |

**成功响应**：

```json
{
  "code": 0,
  "data": {
    "hazard_id": "HD-20260812-0001",
    "status": "pending",
    "created_at": "2026-08-12T10:30:00+08:00"
  }
}
```

**错误码**：`40001` 参数校验失败、`40002` 图片数量超限、`40003` 视频大小超限

---

### 3.2 隐患列表

```
GET /hazards
```

> **对应功能**：H02  
> Admin 可查看全部，SafetyOfficer 可查看管辖范围，Employee 仅可查看本人上报

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `page` | int | 否 | 页码 |
| `page_size` | int | 否 | 每页条数（10/20/50） |
| `status` | string | 否 | 状态筛选：`pending` / `processing` / `pending_review` / `closed` / `rejected`，多选用逗号分隔 |
| `level` | string | 否 | 等级筛选，多选用逗号分隔 |
| `category` | string | 否 | 类别筛选 |
| `project` | string | 否 | 项目筛选 |
| `keyword` | string | 否 | 关键字搜索（标题/编号/描述） |
| `date_from` | string | 否 | 上报起始时间 |
| `date_to` | string | 否 | 上报截止时间 |
| `sort_by` | string | 否 | `created_at` 或 `urgency`，默认 `created_at` |
| `sort_order` | string | 否 | `asc` / `desc`，默认 `desc` |

**响应数据**：分页格式，`items` 为 hazard 摘要对象数组：

```json
{
  "hazard_id": "HD-20260812-0001",
  "title": "3号桥墩临边防护缺失",
  "level": "major",
  "status": "pending",
  "category": "edge_protection",
  "reporter_name": "张三",
  "project": "成绵高速扩容项目",
  "created_at": "2026-08-12T10:30:00+08:00",
  "thumbnail_url": "https://..."
}
```

---

### 3.3 隐患详情

```
GET /hazards/{hazard_id}
```

> **对应功能**：H03  
> 权限同 3.2

**响应数据**：

```json
{
  "code": 0,
  "data": {
    "hazard_id": "HD-20260812-0001",
    "title": "3号桥墩临边防护缺失",
    "description": "桥墩施工区域临边护栏缺失约5米...",
    "level": "major",
    "category": "edge_protection",
    "location": "K12+350 3号桥墩",
    "location_coords": "104.12345,30.67890",
    "project": "成绵高速扩容项目",
    "reporter": { "id": "U001", "name": "张三" },
    "occurred_at": "2026-08-12T09:30:00+08:00",
    "created_at": "2026-08-12T10:30:00+08:00",
    "status": "processing",
    "media": {
      "images": ["https://..."],
      "videos": ["https://..."]
    },
    "timeline": [
      {
        "node": "上报",
        "operator": "张三",
        "time": "2026-08-12T10:30:00+08:00",
        "note": "隐患首次上报"
      },
      {
        "node": "派单",
        "operator": "李四",
        "time": "2026-08-12T11:00:00+08:00",
        "note": "指派王五处理，截止2026-08-15"
      }
    ],
    "assignment": {
      "assignee": { "id": "U003", "name": "王五" },
      "requirements": "立即设置临时防护，48小时内安装正式护栏",
      "deadline": "2026-08-15T18:00:00+08:00",
      "priority": "urgent",
      "attachments": []
    },
    "rectification": null
  }
}
```

**错误码**：`40401` 隐患不存在、`40301` 无权查看该隐患

---

### 3.4 隐患派单

```
POST /hazards/{hazard_id}/assign
```

> **角色**：Admin / SafetyOfficer  
> **对应功能**：H04

**请求体**：

```json
{
  "assignee_id": "U003",
  "requirements": "立即设置临时防护，48小时内安装正式护栏",
  "deadline": "2026-08-15T18:00:00+08:00",
  "priority": "urgent",
  "attachments": []
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `assignee_id` | string | 是 | 整改责任人用户 ID |
| `requirements` | string | 是 | 整改要求（≤ 1000 字） |
| `deadline` | string | 是 | 整改截止日期（不早于当前日期） |
| `priority` | string | 是 | `urgent` / `high` / `medium` / `low` |
| `attachments` | file[] | 否 | 附件（最多 5 个） |

**成功响应**：

```json
{
  "code": 0,
  "data": {
    "hazard_id": "HD-20260812-0001",
    "status": "processing",
    "assigned_at": "2026-08-12T11:00:00+08:00"
  }
}
```

**错误码**：`40004` 隐患状态不允许派单、`40005` 整改截止日期不合法、`40006` 重大隐患整改期限不得超过 7 天

---

### 3.5 整改反馈

```
POST /hazards/{hazard_id}/rectify
```

> **角色**：Admin / SafetyOfficer / Employee（被指派人）  
> **对应功能**：H05

**请求体**（`multipart/form-data`）：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `measures` | string | 是 | 整改措施描述（≥ 20 字） |
| `images_after` | file[] | 是 | 整改后照片（至少 1 张，最多 9 张） |
| `attachments` | file[] | 否 | 相关附件 |
| `completed_at` | string | 否 | 完成时间，默认当前时间 |

**成功响应**：

```json
{
  "code": 0,
  "data": {
    "hazard_id": "HD-20260812-0001",
    "status": "pending_review",
    "rectified_at": "2026-08-13T16:00:00+08:00"
  }
}
```

**错误码**：`40007` 隐患状态不允许提交整改、`40008` 整改描述不足 20 字、`40009` 未上传整改后照片、`40302` 非被指派人无权操作

---

### 3.6 隐患验收

```
POST /hazards/{hazard_id}/review
```

> **角色**：Admin / SafetyOfficer  
> **对应功能**：H06

**请求体**：

```json
{
  "result": "approved",
  "comment": "整改达标，防护设施安装规范",
  "attachments": []
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `result` | string | 是 | `approved`（通过）/ `rejected`（驳回） |
| `comment` | string | 条件必填 | 验收意见。驳回时必填且 ≥ 10 字，通过时选填 |
| `attachments` | file[] | 否 | 验收附件 |

**成功响应**：

```json
{
  "code": 0,
  "data": {
    "hazard_id": "HD-20260812-0001",
    "status": "closed",
    "reviewed_at": "2026-08-14T09:00:00+08:00"
  }
}
```

**错误码**：`40010` 隐患状态不允许验收、`40011` 驳回时必须填写原因（≥ 10 字）

---

### 3.7 隐患导出

```
GET /hazards/{hazard_id}/export
```

> **对应功能**：H03（导出功能）

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `format` | string | 否 | 导出格式，默认 `pdf` |

**响应**：返回文件流，Content-Type 为对应文件 MIME 类型。

---

## 4. AI 智能助手

### 4.1 AI 问答（流式）

```
POST /ai/chat
```

> **角色**：Admin / SafetyOfficer / Employee  
> **对应功能**：A01、A03、A05、A06

**请求头**：

```
Accept: text/event-stream
Content-Type: application/json
```

**请求体**：

```json
{
  "session_id": "sess_abc123",
  "question": "高处作业安全带的使用标准是什么？"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `session_id` | string | 否 | 会话 ID。首次提问不传，服务端返回新 session_id |
| `question` | string | 是 | 用户问题（≤ 500 字） |

**SSE 流式响应**：

```
event: token
data: 根据

event: token
data: 《高处作业

event: token
data: 安全技术规范》

...

event: done
data: {"session_id": "sess_abc123", "message_id": "msg_001"}

event: sources
data: [{"doc_name":"高处作业安全技术规范","section":"第5.2条","excerpt":"安全带应高挂低用..."}]
```

**SSE 事件类型**：

| 事件 | 说明 |
|------|------|
| `token` | AI 回答的文本片段（逐 token） |
| `done` | 回答完成，附带 session_id 和 message_id |
| `sources` | 引用来源列表 |
| `error` | 发生错误时的错误信息 |

**错误码（error 事件）**：`40201` 敏感词拦截、`40202` 非安全相关问题（引导重定向）、`40203` AI 服务不可用

---

### 4.2 停止生成

```
POST /ai/chat/{message_id}/stop
```

> **对应功能**：A03（停止生成）

**请求体**：无

**成功响应**：`{ "code": 0, "message": "生成已停止" }`

中断后的消息标记为 `interrupted`，已输出的部分内容保留。

---

### 4.3 获取会话列表

```
GET /ai/sessions
```

> **对应功能**：A02

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `page` | int | 否 | 页码 |
| `page_size` | int | 否 | 每页条数（默认 20） |
| `keyword` | string | 否 | 按会话标题搜索 |

**响应数据**：

```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "session_id": "sess_abc123",
        "title": "高处作业安全带使用标准",
        "last_message": "安全带应高挂低用...",
        "message_count": 6,
        "updated_at": "2026-08-12T10:30:00+08:00"
      }
    ],
    "total": 15,
    "page": 1,
    "page_size": 20
  }
}
```

---

### 4.4 创建新会话

```
POST /ai/sessions
```

> **对应功能**：A02

**请求体**：无（或 `{}`）

**响应**：

```json
{
  "code": 0,
  "data": {
    "session_id": "sess_new456",
    "title": "新对话",
    "created_at": "2026-08-12T10:45:00+08:00"
  }
}
```

---

### 4.5 获取会话消息

```
GET /ai/sessions/{session_id}/messages
```

> **对应功能**：A02

**响应数据**：

```json
{
  "code": 0,
  "data": {
    "session_id": "sess_abc123",
    "title": "高处作业安全带使用标准",
    "messages": [
      {
        "message_id": "msg_001",
        "role": "user",
        "content": "高处作业安全带的使用标准是什么？",
        "created_at": "2026-08-12T10:25:00+08:00"
      },
      {
        "message_id": "msg_002",
        "role": "assistant",
        "content": "根据《高处作业安全技术规范》第5.2条...",
        "sources": [{ "doc_name": "...", "section": "...", "excerpt": "..." }],
        "status": "completed",
        "created_at": "2026-08-12T10:25:05+08:00"
      }
    ]
  }
}
```

---

### 4.6 编辑会话标题

```
PUT /ai/sessions/{session_id}
```

> **对应功能**：A02

**请求体**：

```json
{
  "title": "高处作业安全规范问答"
}
```

---

### 4.7 删除会话

```
DELETE /ai/sessions/{session_id}
```

> **对应功能**：A02

**请求体**：无

**成功响应**：`{ "code": 0, "message": "会话已删除" }`

---

### 4.8 批量删除会话

```
POST /ai/sessions/batch-delete
```

**请求体**：

```json
{
  "session_ids": ["sess_abc", "sess_def", "sess_ghi"]
}
```

---

### 4.9 获取快捷问题

```
GET /ai/quick-questions
```

> **对应功能**：A04

**响应数据**：

```json
{
  "code": 0,
  "data": {
    "categories": [
      {
        "name": "法律法规",
        "icon": "law",
        "questions": [
          "安全生产法对从业人员的权利有哪些规定？",
          "三同时制度的具体要求是什么？"
        ]
      },
      {
        "name": "操作规程",
        "icon": "operation",
        "questions": [
          "高处作业安全带佩戴规范？",
          "动火作业审批流程是什么？"
        ]
      }
    ],
    "hot_questions": [
      "什么是重大事故隐患判定标准？"
    ]
  }
}
```

---

### 4.10 点赞/踩

```
POST /ai/messages/{message_id}/feedback
```

> **对应功能**：A07

**请求体**：

```json
{
  "rating": "dislike",
  "reasons": ["inaccurate", "incomplete"],
  "comment": "回答遗漏了2025年新版规范的内容"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `rating` | string | 是 | `like` / `dislike` |
| `reasons` | string[] | 否（like 时忽略） | 踩的原因：`inaccurate` / `incomplete` / `misunderstanding` / `off_topic` / `other` |
| `comment` | string | 否 | 补充说明（≤ 200 字） |

**成功响应**：`{ "code": 0, "message": "反馈已提交" }`

**错误码**：`40012` 重复评价（同一用户同一消息只允许评价一次）

---

### 4.11 取消评价

```
DELETE /ai/messages/{message_id}/feedback
```

> **对应功能**：A07（取消评价后允许重新评价）

---

## 5. 考试工坊

### 5.1 题库管理

#### 5.1.1 题目列表

```
GET /exam/questions
```

> **角色**：Admin / SafetyOfficer  
> **对应功能**：E01

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `page` | int | 否 | 页码 |
| `page_size` | int | 否 | 每页条数 |
| `type` | string | 否 | 题型：`single_choice` / `multi_choice` / `true_false` / `fill_blank` / `essay` |
| `difficulty` | string | 否 | 难度：`easy` / `medium` / `hard` |
| `category_id` | int | 否 | 分类 ID |
| `tag` | string | 否 | 标签筛选 |
| `status` | string | 否 | 状态：`draft` / `pending_review` / `published` / `rejected` |
| `keyword` | string | 否 | 题干关键字搜索 |

**响应数据**：分页格式。

---

#### 5.1.2 题目详情

```
GET /exam/questions/{question_id}
```

---

#### 5.1.3 手动录入题目

```
POST /exam/questions
```

> **对应功能**：E01

**请求体**：

```json
{
  "type": "single_choice",
  "content": "根据《安全生产法》，从业人员有权对本单位安全生产工作中存在的问题提出批评、(  )、控告。",
  "options": {
    "A": "检举",
    "B": "举报",
    "C": "投诉",
    "D": "建议"
  },
  "answer": "B",
  "explanation": "根据《安全生产法》第五十七条...",
  "score": 2,
  "difficulty": "medium",
  "category_id": 1,
  "tags": ["安全生产法", "从业人员权利"]
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 是 | 题型 |
| `content` | string | 是 | 题干 |
| `options` | object | 条件必填 | 客观题的选项（简答题不传） |
| `answer` | string | 是 | 正确答案。客观题为选项 key（单选"A"、多选"AB"），判断为"正确"/"错误"，填空为逗号分隔的答案 |
| `explanation` | string | 是 | 解析 |
| `score` | float | 是 | 分值 |
| `difficulty` | string | 是 | 难度等级 |
| `category_id` | int | 否 | 分类 ID |
| `tags` | string[] | 否 | 标签 |

**多选题 answer 格式**：`"ABD"`（正确选项字母拼接）

**填空题 answer 格式**：`"根部,根部"`（每空答案用逗号分隔）

---

#### 5.1.4 编辑题目

```
PUT /exam/questions/{question_id}
```

---

#### 5.1.5 删除题目

```
DELETE /exam/questions/{question_id}
```

> 已被试卷引用的题目不可物理删除，返回错误码 `40021`。

---

#### 5.1.6 批量导入题目

```
POST /exam/questions/import
```

> **对应功能**：E01

**请求体**（`multipart/form-data`）：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | file | 是 | Excel 文件（.xlsx） |

**Excel 模板字段**：题型、题干、选项A~H、正确答案、解析、分值、难度、分类、标签

**成功响应**：

```json
{
  "code": 0,
  "data": {
    "total": 150,
    "success": 142,
    "failed": 8,
    "errors": [
      { "row": 5, "reason": "正确答案'X'不在选项范围内" },
      { "row": 23, "reason": "题干长度超过2000字限制" }
    ]
  }
}
```

---

#### 5.1.7 下载导入模板

```
GET /exam/questions/template
```

返回 Excel 模板文件流。

---

#### 5.1.8 题目查重检测

```
POST /exam/questions/check-duplicate
```

**请求体**：

```json
{
  "content": "根据《安全生产法》，从业人员有权..."
}
```

**响应**：

```json
{
  "code": 0,
  "data": {
    "has_duplicate": true,
    "similar_questions": [
      {
        "question_id": 1024,
        "content": "依据《安全生产法》...",
        "similarity": 0.87
      }
    ]
  }
}
```

---

### 5.2 AI 出题

```
POST /exam/ai/generate
```

> **角色**：Admin / SafetyOfficer  
> **对应功能**：E02

**请求体**：

```json
{
  "mode": "knowledge",
  "knowledge_points": ["高处作业安全", "安全带使用规范"],
  "types": ["single_choice", "true_false"],
  "count": 10,
  "difficulty": "mixed",
  "use_knowledge_base": true
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `mode` | string | 是 | 出题方式：`knowledge`（知识点出题）/ `document`（文档出题）/ `free`（自由出题） |
| `knowledge_points` | string[] | 否 | 知识点列表（mode=knowledge 时必填） |
| `document_id` | int | 否 | 文档 ID（mode=document 时必填） |
| `topic` | string | 否 | 自由主题（mode=free 时必填） |
| `types` | string[] | 是 | 题型列表 |
| `count` | int | 是 | 生成数量（1-50） |
| `difficulty` | string | 是 | `easy` / `medium` / `hard` / `mixed` |
| `use_knowledge_base` | bool | 否 | 是否基于知识库出题，默认 true |

**SSE 流式响应**（首题 ≤ 5 秒返回）：

```
event: question
data: {"index":1,"type":"single_choice","content":"...","options":{...},"answer":"B","explanation":"...","difficulty":"medium"}

event: question
data: {"index":2,...}

...

event: done
data: {"generation_id":"gen_001","count":10}
```

**最终生成的问题进入「待审核」状态**。

---

### 5.3 试卷管理

#### 5.3.1 试卷列表

```
GET /exam/papers
```

> **角色**：Admin / SafetyOfficer  
> **对应功能**：E03

**查询参数**：`page`、`page_size`、`status`（draft / published / ended）、`keyword`

---

#### 5.3.2 创建试卷（手动组卷）

```
POST /exam/papers
```

> **对应功能**：E03

**请求体**：

```json
{
  "title": "2026年第三季度安全考试",
  "description": "全员安全生产知识考核",
  "mode": "manual",
  "questions": [
    { "question_id": 101, "score": 2, "order": 1 },
    { "question_id": 102, "score": 2, "order": 2 }
  ],
  "config": {
    "duration": 60,
    "pass_score": 60,
    "total_score": 100,
    "shuffle_questions": true,
    "shuffle_options": true,
    "anti_cheat": true,
    "max_switch_count": 3,
    "allow_retake": true,
    "max_retake_count": 2,
    "start_time": "2026-08-15T09:00:00+08:00",
    "end_time": "2026-08-15T18:00:00+08:00"
  },
  "assignees": {
    "type": "department",
    "ids": ["dept_eng", "dept_safety"]
  }
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | 是 | 试卷标题 |
| `description` | string | 否 | 考试说明 |
| `mode` | string | 是 | `manual`（手动组卷） |
| `questions` | array | 是 | 题目列表 |
| `config.duration` | int | 是 | 考试时长（分钟） |
| `config.pass_score` | float | 是 | 及格分数 |
| `config.shuffle_questions` | bool | 否 | 题目乱序，默认 false |
| `config.shuffle_options` | bool | 否 | 选项乱序，默认 false |
| `config.anti_cheat` | bool | 否 | 切屏检测，默认 false |
| `config.max_switch_count` | int | 否 | 允许切屏次数，anti_cheat=true 时生效 |
| `config.allow_retake` | bool | 否 | 允许重考，默认 false |
| `config.max_retake_count` | int | 否 | 最大重考次数 |
| `config.start_time` | string | 是 | 考试开始时间 |
| `config.end_time` | string | 是 | 考试结束时间 |
| `assignees` | object | 是 | 指派考生（按部门/项目/用户指定） |

---

#### 5.3.3 创建试卷（智能组卷）

```
POST /exam/papers
```

> **对应功能**：E03

**请求体**（mode=auto）：

```json
{
  "title": "2026年第三季度安全考试",
  "mode": "auto",
  "strategy": {
    "total_score": 100,
    "distribution": [
      { "type": "single_choice", "count": 20, "score_per": 2 },
      { "type": "multi_choice", "count": 10, "score_per": 3 },
      { "type": "true_false", "count": 10, "score_per": 2 },
      { "type": "essay", "count": 1, "score_per": 10 }
    ],
    "difficulty_ratio": { "easy": 0.4, "medium": 0.4, "hard": 0.2 },
    "category_coverage": [
      { "category_id": 1, "ratio": 0.4 },
      { "category_id": 2, "ratio": 0.3 }
    ]
  },
  "config": { ... },
  "assignees": { ... }
}
```

---

#### 5.3.4 试卷详情

```
GET /exam/papers/{paper_id}
```

---

#### 5.3.5 编辑试卷

```
PUT /exam/papers/{paper_id}
```

> 仅「草稿」状态可编辑。

---

#### 5.3.6 替换题目

```
PUT /exam/papers/{paper_id}/questions/{index}
```

> 替换试卷中某一题，从题库随机抽取同类型同难度题目。

**请求体**：

```json
{
  "type": "single_choice",
  "difficulty": "medium",
  "category_id": 1
}
```

---

#### 5.3.7 删除试卷

```
DELETE /exam/papers/{paper_id}
```

---

#### 5.3.8 发布试卷

```
POST /exam/papers/{paper_id}/publish
```

> 状态从「草稿」变为「已发布」，向指派考生推送通知。

---

#### 5.3.9 结束考试

```
POST /exam/papers/{paper_id}/end
```

> 手动提前结束考试。

---

### 5.4 在线考试

#### 5.4.1 我的考试列表

```
GET /exam/my-exams
```

> **角色**：Employee（Admin/SafetyOfficer 也可查看）  
> **对应功能**：E04/E06

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `status` | string | 否 | `upcoming` / `ongoing` / `finished` |
| `page` | int | 否 | 页码 |

---

#### 5.4.2 进入考试

```
POST /exam/my-exams/{paper_id}/start
```

> **对应功能**：E04

**响应**：

```json
{
  "code": 0,
  "data": {
    "attempt_id": "attempt_001",
    "paper": {
      "title": "2026年第三季度安全考试",
      "duration": 3600,
      "total_score": 100,
      "pass_score": 60,
      "questions": [
        {
          "index": 1,
          "question_id": 101,
          "type": "single_choice",
          "content": "根据《安全生产法》...",
          "options": { "A": "...", "B": "...", "C": "...", "D": "..." },
          "score": 2
        }
      ],
      "config": {
        "shuffle_questions": true,
        "shuffle_options": true,
        "anti_cheat": true,
        "max_switch_count": 3
      },
      "started_at": "2026-08-15T10:00:00+08:00",
      "ends_at": "2026-08-15T11:00:00+08:00"
    }
  }
}
```

**错误码**：`40022` 不在考试时间窗口、`40023` 重考次数已用完、`40024` 已通过考试不可重考

---

#### 5.4.3 提交答案（逐题保存）

```
POST /exam/attempts/{attempt_id}/answers
```

> **对应功能**：E04

**请求体**：

```json
{
  "question_index": 1,
  "answer": "B"
}
```

多选答案格式：`"ABD"`。前端应每 10 秒自动保存一次答案。

---

#### 5.4.4 标记题目

```
POST /exam/attempts/{attempt_id}/mark/{question_index}
```

**请求体**：

```json
{
  "marked": true
}
```

---

#### 5.4.5 批量保存答案

```
PUT /exam/attempts/{attempt_id}/answers
```

> 断线重连后批量同步答案。

**请求体**：

```json
{
  "answers": [
    { "question_index": 1, "answer": "B" },
    { "question_index": 2, "answer": "正确" },
    { "question_index": 3, "answer": "根" }
  ]
}
```

---

#### 5.4.6 交卷

```
POST /exam/attempts/{attempt_id}/submit
```

> **对应功能**：E04

**请求体**：无

**成功响应**：

```json
{
  "code": 0,
  "data": {
    "attempt_id": "attempt_001",
    "submitted_at": "2026-08-15T10:35:00+08:00",
    "message": "试卷已提交，正在阅卷中"
  }
}
```

**错误码**：`40025` 已交卷不可再次提交

---

#### 5.4.7 获取考试结果

```
GET /exam/attempts/{attempt_id}/result
```

> **对应功能**：E06

**响应**：

```json
{
  "code": 0,
  "data": {
    "attempt_id": "attempt_001",
    "paper_title": "2026年第三季度安全考试",
    "total_score": 85,
    "pass_score": 60,
    "passed": true,
    "duration_used": 2100,
    "status": "scored",
    "submitted_at": "2026-08-15T10:35:00+08:00",
    "details": [
      {
        "index": 1,
        "type": "single_choice",
        "content": "根据《安全生产法》...",
        "options": { "A": "...", "B": "...", "C": "...", "D": "..." },
        "user_answer": "B",
        "correct_answer": "B",
        "score": 2,
        "max_score": 2,
        "explanation": "根据《安全生产法》第五十七条...",
        "ai_feedback": null
      }
    ]
  }
}
```

---

#### 5.4.8 切屏记录上报

```
POST /exam/attempts/{attempt_id}/switch-event
```

> **对应功能**：E04

**请求体**：

```json
{
  "timestamp": "2026-08-15T10:05:30+08:00"
}
```

**响应**：

```json
{
  "code": 0,
  "data": {
    "switch_count": 2,
    "max_count": 3,
    "warning": "您已切屏 2 次，超过 3 次将自动交卷"
  }
}
```

---

### 5.5 自动阅卷

#### 5.5.1 获取待阅卷列表

```
GET /exam/grading/pending
```

> **角色**：Admin / SafetyOfficer  
> **对应功能**：E05

**查询参数**：`paper_id`、`page`、`page_size`

---

#### 5.5.2 阅卷详情

```
GET /exam/grading/{attempt_id}
```

> 展示所有题目 + 客观题自动评分 + 简答题 AI 评分建议。

---

#### 5.5.3 手动调整分数

```
PUT /exam/grading/{attempt_id}/score/{question_index}
```

> **对应功能**：E05

**请求体**：

```json
{
  "score": 8,
  "comment": "答案基本正确，但缺少关键步骤说明"
}
```

---

#### 5.5.4 发布成绩

```
POST /exam/grading/{attempt_id}/publish
```

> 安全员确认后发布，考生可查看成绩。

---

### 5.6 题目审核

#### 5.6.1 待审核列表

```
GET /exam/review/pending
```

> **角色**：Admin / SafetyOfficer  
> **对应功能**：E08

**查询参数**：`page`、`page_size`、`type`（题型筛选）、`keyword`

---

#### 5.6.2 审核单题

```
POST /exam/review/{question_id}
```

> **对应功能**：E08

**请求体**：

```json
{
  "action": "approve",
  "comment": ""
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `action` | string | 是 | `approve` / `reject` / `edit_approve` |
| `comment` | string | 条件必填 | 驳回时必填 |
| `edited_content` | object | 否 | 编辑后的题目内容（action=edit_approve 时必填） |

---

#### 5.6.3 批量审核

```
POST /exam/review/batch
```

**请求体**：

```json
{
  "question_ids": [101, 102, 103],
  "action": "approve"
}
```

> 单次批量 ≤ 50 题

---

## 6. 消息通知

### 6.1 消息列表

```
GET /notifications
```

> **对应功能**：H08

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `page` | int | 否 | 页码 |
| `page_size` | int | 否 | 每页条数（默认 20） |
| `is_read` | bool | 否 | 已读/未读筛选 |

**响应数据**：分页格式，`items` 为通知对象数组：

```json
{
  "notification_id": "notif_001",
  "type": "hazard_assigned",
  "title": "您有一条新的隐患整改任务",
  "content": "安全员李四指派您处理隐患 [HD-20260812-0001]...",
  "is_read": false,
  "target_type": "hazard",
  "target_id": "HD-20260812-0001",
  "created_at": "2026-08-12T11:00:05+08:00"
}
```

**通知类型**：

| type | 说明 |
|------|------|
| `hazard_assigned` | 隐患被派单 |
| `rectification_submitted` | 整改反馈已提交 |
| `review_result` | 验收结果（通过/驳回） |
| `rectification_urge` | 整改催办 |
| `exam_notification` | 考试通知 |
| `score_published` | 成绩发布 |

---

### 6.2 未读消息数量

```
GET /notifications/unread-count
```

**响应**：

```json
{
  "code": 0,
  "data": { "count": 5 }
}
```

---

### 6.3 标记已读

```
PUT /notifications/{notification_id}/read
```

---

### 6.4 全部标记已读

```
POST /notifications/read-all
```

---

### 6.5 消息偏好设置

```
GET /notifications/preferences
PUT /notifications/preferences
```

**请求体**（PUT）：

```json
{
  "hazard_assigned": true,
  "rectification_submitted": true,
  "review_result": true,
  "rectification_urge": true,
  "exam_notification": true,
  "score_published": true
}
```

---

## 7. 统计分析

### 7.1 隐患统计看板

```
GET /statistics/hazards/overview
```

> **角色**：Admin（全局）/ SafetyOfficer（管辖范围）  
> **对应功能**：H07

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `date_from` | string | 否 | 起始时间 |
| `date_to` | string | 否 | 截止时间 |

**响应**：

```json
{
  "code": 0,
  "data": {
    "overview": {
      "total": 1250,
      "pending": 45,
      "processing": 120,
      "pending_review": 85,
      "closed": 950,
      "closure_rate": 0.92,
      "avg_closure_hours": 48.5
    },
    "trend": [
      { "date": "2026-08-01", "reported": 15, "closed": 10 },
      { "date": "2026-08-02", "reported": 20, "closed": 18 }
    ],
    "level_distribution": {
      "critical": 50,
      "major": 200,
      "minor": 600,
      "trivial": 400
    },
    "category_distribution": {
      "height_work": 300,
      "edge_protection": 250,
      "machinery": 200,
      "fire_safety": 150,
      "temp_electricity": 100
    }
  }
}
```

---

### 7.2 隐患趋势数据

```
GET /statistics/hazards/trend
```

> 查询参数：`date_from`、`date_to`、`granularity`（`day` / `week` / `month` / `quarter`）

---

### 7.3 闭环率排名

```
GET /statistics/hazards/closure-ranking
```

> 查询参数：`date_from`、`date_to`、`group_by`（`project` / `officer`）

---

### 7.4 考试统计看板

```
GET /statistics/exams/overview
```

> **角色**：Admin（全局）/ SafetyOfficer（管辖范围）  
> **对应功能**：E07

**查询参数**：`date_from`、`date_to`

**响应**：

```json
{
  "code": 0,
  "data": {
    "overview": {
      "total_exams": 85,
      "total_attempts": 3200,
      "avg_participation_rate": 0.88,
      "avg_pass_rate": 0.82,
      "avg_score": 76.5
    },
    "score_distribution": {
      "above_90": 500,
      "80_89": 800,
      "70_79": 600,
      "60_69": 400,
      "below_60": 900
    },
    "knowledge_heatmap": [
      { "category": "法律法规", "accuracy": 0.85 },
      { "category": "操作规程", "accuracy": 0.72 }
    ]
  }
}
```

---

### 7.5 单场考试分析

```
GET /statistics/exams/{paper_id}
```

**响应**：包含参考率、成绩直方图、每题得分率、错题 TOP 榜。

---

### 7.6 错题 TOP 榜

```
GET /statistics/exams/top-errors
```

> 查询参数：`date_from`、`date_to`、`limit`（默认 20）

---

### 7.7 AI 问答满意度统计

```
GET /statistics/ai-satisfaction
```

> **角色**：Admin  
> **对应功能**：A07

**查询参数**：`date_from`、`date_to`

**响应**：

```json
{
  "code": 0,
  "data": {
    "total_feedback": 5000,
    "like_rate": 0.78,
    "dislike_reasons": {
      "inaccurate": 300,
      "incomplete": 200,
      "misunderstanding": 150,
      "off_topic": 50,
      "other": 100
    }
  }
}
```

---

### 7.8 统计报表导出

```
GET /statistics/export
```

> **角色**：Admin / SafetyOfficer

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `module` | string | 是 | `hazards` / `exams` |
| `date_from` | string | 是 | 起始时间 |
| `date_to` | string | 是 | 截止时间 |
| `format` | string | 否 | 导出格式，默认 `xlsx` |

返回文件流，Content-Type 为对应格式 MIME 类型。

---

## 8. 知识库管理

### 8.1 知识库文档列表

```
GET /knowledge/documents
```

> **角色**：Admin / SafetyOfficer  
> **对应功能**：A05（管理端）

**查询参数**：`page`、`page_size`、`type`、`status`、`keyword`

---

### 8.2 上传文档

```
POST /knowledge/documents
```

> **角色**：Admin  
> **对应功能**：A05

**请求体**（`multipart/form-data`）：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | file | 是 | 文档文件（PDF/Word/TXT/Markdown，≤ 50MB） |
| `title` | string | 是 | 文档标题 |
| `doc_type` | string | 是 | 文档类型：`regulation` / `procedure` / `case` / `emergency` / `other` |
| `category_id` | int | 否 | 分类 ID |
| `tags` | string[] | 否 | 标签 |
| `authority_level` | string | 否 | 权威等级：`A` / `B` / `C`，默认 `B` |

**响应**：

```json
{
  "code": 0,
  "data": {
    "document_id": 245,
    "status": "parsing",
    "message": "文档已上传，正在解析和向量化处理中"
  }
}
```

---

### 8.3 文档解析状态查询

```
GET /knowledge/documents/{doc_id}/status
```

**响应**：`parsing` → `chunking` → `indexing` → `indexed`

---

### 8.4 删除文档

```
DELETE /knowledge/documents/{doc_id}
```

> **角色**：Admin  
> 同时删除关联向量和分块数据。

---

### 8.5 知识库分类管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/knowledge/categories` | 分类树 |
| `POST` | `/knowledge/categories` | 创建分类 |
| `PUT` | `/knowledge/categories/{id}` | 编辑分类 |
| `DELETE` | `/knowledge/categories/{id}` | 删除分类（无文档时可删） |

---

### 8.6 快捷问题管理

| 方法 | 路径 | 说明 | 角色 |
|------|------|------|------|
| `GET` | `/ai/quick-questions/admin` | 获取全部快捷问题列表 | Admin |
| `POST` | `/ai/quick-questions` | 添加快捷问题 | Admin |
| `PUT` | `/ai/quick-questions/{id}` | 编辑快捷问题 | Admin |
| `DELETE` | `/ai/quick-questions/{id}` | 删除快捷问题 | Admin |

**请求体（创建/编辑）**：

```json
{
  "category": "法规类",
  "category_icon": "law",
  "question": "安全生产法对从业人员的权利有哪些规定？",
  "roles": ["Employee", "SafetyOfficer"],
  "is_hot": false
}
```

---

## 附录：错误码参考

### HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未认证或 Token 过期 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 409 | 资源冲突（如重复提交） |
| 413 | 上传文件过大 |
| 429 | 请求频率超限 |
| 500 | 服务器内部错误 |
| 503 | 服务暂不可用（如 AI 服务降级） |

### 业务错误码

| 错误码 | 说明 |
|--------|------|
| 0 | 成功 |
| **认证 (401xx)** | |
| 40101 | 用户名或密码错误 |
| 40102 | 账户已被禁用 |
| 40103 | refresh_token 无效或已过期 |
| 40104 | 旧密码错误 |
| **通用 (400xx)** | |
| 40001 | 参数校验失败 |
| 40002 | 图片数量超限（最多 9 张） |
| 40003 | 视频文件过大（单段 ≤ 50MB） |
| 40004 | 隐患状态不允许当前操作 |
| 40005 | 整改截止日期不合法 |
| 40006 | 重大隐患整改期限不得超过 7 天 |
| 40007 | 隐患状态不允许提交整改 |
| 40008 | 整改描述不足 20 字 |
| 40009 | 未上传整改后照片 |
| 40010 | 隐患状态不允许验收 |
| 40011 | 驳回时必须填写原因（≥ 10 字） |
| 40012 | 重复评价 |
| 40021 | 题目已被试卷引用，不可删除 |
| 40022 | 不在考试时间窗口 |
| 40023 | 重考次数已用完 |
| 40024 | 已通过考试不可重考 |
| 40025 | 已交卷不可再次提交 |
| **权限 (403xx)** | |
| 40301 | 无权查看该隐患 |
| 40302 | 非被指派人无权操作 |
| 40303 | 角色无此功能权限 |
| **AI (402xx)** | |
| 40201 | 问题包含敏感内容 |
| 40202 | 非安全相关问题 |
| 40203 | AI 服务暂不可用 |
| 40204 | 会话数量已达上限（100 个） |
| **资源 (404xx)** | |
| 40401 | 隐患不存在 |
| 40402 | 会话不存在 |
| 40403 | 试卷不存在 |
| 40404 | 题目不存在 |
| **限流 (429xx)** | |
| 42901 | AI 问答频率超限（≤ 10 次/分钟） |
| 42902 | 请求频率超限 |

---

> **文档结束** | 蜀道安全助手 API 接口文档 V1.0  
> 共 8 大模块、60+ 接口，覆盖隐患管理、AI 问答、考试工坊、消息通知、统计分析、知识库管理全部功能。
*（内容由AI生成，仅供参考）*
