# 保险精准营销系统

基于 Flask 的保险客户精准营销控制台。系统导入健康险交叉销售数据，训练 LR、XGBoost、RandomForest 三类模型，根据 ROC-AUC 选择最佳模型并回写客户购买概率；随后可为高潜客户生成个性化营销邮件。

## 运行

项目使用全局 Python 3.12。安装依赖后复制 `.env.example` 为 `.env`，按需填写 LLM 配置：

```powershell
python -m pip install -r requirements.txt
python run_flask.py
```

浏览器打开 `http://127.0.0.1:5000`，初始管理员账号为 `admin` / `admin123`。在“客户数据”页上传根目录的 `data.xlsx`，然后按“模型中心 → 概率预测 → 营销邮件”完成流程。

## 后端调试终端

使用 Rich 终端在进程内调用 Flask 后端，不需要启动 HTTP 服务：

```powershell
python debug_terminal.py
```

常用命令：

```text
routes auth
login admin admin123
request GET /api/v1/data/statistics
request GET /api/v1/data/customers --query page=1 --query per_page=5
request POST /api/v1/auth/login --json '{"username":"admin","password":"admin123"}'
request POST /api/v1/data/upload --file data.xlsx
history
```

终端会在当前会话中自动保存登录后的 JWT，并为后续请求注入 `Authorization` 请求头。也可以使用 `--command` 重放命令，适合脚本化冒烟检查。

## 测试

```powershell
python -m pytest
python -m ruff check .
```

测试使用临时 SQLite 数据库和内存 Excel，不会使用根目录数据或访问 LLM 服务。

## 结构

- `app/api/v1`：HTTP 路由和 RBAC 入口
- `app/services`：数据导入、建模、LLM 邮件等业务流程
- `app/models`：SQLAlchemy 数据模型
- `app/core`：配置、数据库、JWT、统一异常响应
- `app/static`：原生 JavaScript 单页管理后台
