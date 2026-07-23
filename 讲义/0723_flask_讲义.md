# 0723 工作目标

- 回顾

- flask介绍和实战

- postman的使用

- fastapi的mvc：项目逻辑，整个项目
  
  

## 模块0： http/requests/爬虫逻辑/实战

- 后续抽空看一下bs4和xpath和css选择器的教程

- 注意爬取时，翻页或者下拉方式爬取的设定

- 精简ai生成的代码，看懂逻辑即可

- 代码讲解的优化建议：搭建框架，框架下的类和函数，伪代码先写先思考，再粘贴正确的代码对比自己的思路是否正确，讲解之后课下消化
  
  

## 模块1：Flask的核心概念与环境搭建

### 0.常用的python的后端开发框架：Flask->fastapi（主流 ）->tornado->Django

### 1.什么是web服务器与Flask？

#### 1.1 web服务器的本质

web服务器是互联网的接待员，负责接收浏览器的请求(比如访问一个网址)，并返回对应的html网页或者数据(json)

浏览器--请求-->服务器--响应-->浏览器--请求-->服务器

整个过程就是HTTP请求-响应循环，Flask是把整个过程快速搭建起来的工具。

#### 1.2 Flask的定义

python 轻量级的web框架，微框架

- 核心极简，只提供最基础的路由和请求处理功能

- 扩展插件来进行扩充

- 相对django，更灵活

- 适用场景：pandas、pytorch、openai ，快速开发原型，api服务，ai应用后端

### 2.Flask 基础语法：

#### 2.1 环境搭建和构建实例

```bash
pip install flask
```

```python
from flask import Flask

#  创建 Flask 引用实例
app = Flask(__name__)
```

Flask:Flask提供的主类，是整个应用的大脑

app:变量名，可以改成任意的名字，如"my_server", 之后的路由和配置都要通过这个变 量

"____name__ __":内置变量，代表当前模块的名字，告诉Flask从哪里加载静态文件（css/js)和模版（html）

- 模板文件都放在template/文件夹里

- 静态文件（CSS/JS/图片）默认放在static/文件里

#### 2.2 路由装饰器：@app.route(‘/’)

```
@app.route('/')  #127.0.0.1:5000/
def index():
    return "<h1>🚀 欢迎进入 Flask 世界！</h1>"
```

@app.route('/'):当前用户访问首页的，执行以下函数

def index():随便取，如果是首页一般默认写index

return  函数返回的内容会直接显示在浏览器里面



**执行流程**：

1. 用户在浏览器输入 `http://127.0.0.1:5000/`
2. Flask 收到请求，查找绑定了“ `/`” 的函数
3. 找到 `index()` 函数并执行它
4. 把函数返回的 HTML 字符串发送给浏览器
5. 浏览器渲染并显示给用户

#### 2.3 动态路由：@app.route('greet/<name>')

最实用和最常用的功能：让url的一部分可以变成一个变量

```
@app.route('/greet/<name>')
def greet(name):
    return f" 你好, {name}！欢迎来到空间站。"
```

<name> :一个占位符，用户访问时添加实际的值

def greet(name)：函数必须接收一个参数，这个参数名必须和尖括号里面的一致

**类型转换器**：

默认情况下，`<name>` 匹配的是字符串。但你可以指定类型：

| 转换器               | 示例                       | 说明         |
| ----------------- | ------------------------ | ---------- |
| `<int:id>`        | `/user/123`              | 只匹配整数      |
| `<float:price>`   | `/price/9.99`            | 只匹配浮点数     |
| `<path:filename>` | `/file/a/b/c.txt`        | 匹配包含斜杠的路径  |
| `<uuid:id>`       | `/item/550e8400-e29b...` | 匹配 UUID 格式 |

#### 2.4 启动服务器：app.run()

```python
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
```

## 模块二：路由配置与请求相应处理

##### 1.http请求方法

HTTP 协议的**请求方法（Method）**：

| 方法         | 含义   | 生活比喻        | 典型用途           |
| ---------- | ---- | ----------- | -------------- |
| **GET**    | 获取数据 | 去图书馆借书看     | 查询用户信息、获取文章列表  |
| **POST**   | 提交数据 | 去邮局寄信       | 注册账号、发布文章、提交表单 |
| **PUT**    | 完整更新 | 重新填写整张表格    | 修改用户全部资料       |
| **PATCH**  | 部分更新 | 只改表格上的一个错别字 | 修改用户头像         |
| **DELETE** | 删除数据 | 撕掉已提交的表格    | 删除文章、注销账号      |

**在 Flask 中指定请求方法**：

```python
# 默认只允许 GET 请求
@app.route('/users')

# 允许 GET 和 POST 请求
@app.route('/users', methods=['GET', 'POST'])

# 只允许 POST 请求
@app.route('/register', methods=['POST'])
```

#### 2.请求与相应对象

Flask提供几个内置对象来处理请求和生成响应

##### 2.1 request 对象：获取用户发来的数据

当用户访问你的网站时，`request` 对象里包含了**所有用户发来的信息**：

| 属性/方法                | 含义               | 使用场景                    |
| -------------------- | ---------------- | ----------------------- |
| `request.method`     | 请求方法（GET/POST 等） | 判断用户是查询还是提交             |
| `request.args`       | URL 查询参数         | `?page=1&limit=10` 中的参数 |
| `request.form`       | 表单数据             | 用户填写的登录表单               |
| `request.get_json()` | JSON 数据          | 前端通过 `fetch` 发送的 JSON   |
| `request.headers`    | 请求头              | 获取 User-Agent、Cookie 等  |
| `request.cookies`    | Cookie           | 读取用户浏览器的 Cookie         |

```python
from flask import Flask, request

#  创建 Flask 引用实例
app = Flask(__name__)

@app.route('/search')
def search():
    # 用户访问 /search?keyword=python&page=2
    keyword = request.args.get('keyword')  # "python"
    page = request.args.get('page', 1)     # "2"（默认值为 1）
    return f"搜索关键词：{keyword}，第 {page} 页"


if __name__ == '__main__':
    app.run(host="127.0.0.1", port=5000, debug=True)   



```

**注意：request.args.get("关键字“，默认值)**

##### 2.2 jsonify 对象：返回json数据

web开发中，前后端分离，后端通常返回的都是json格式的数据，前端JavaScript做渲染

```python
from flask import jsonify

@app.route('/api/user')
def get_user():
    user = {
        "id": 1,
        "name": "张三",
        "email": "zhangsan@example.com"
    }
    # jsonify 会自动：
    # 1. 把 Python 字典转成 JSON 字符串
    # 2. 设置 Content-Type: application/json 响应头
    return jsonify(user)


```

**注意：返回json时的最佳实践**

```
# 标准 API 响应格式
return jsonify({
    "code": 200,        # 状态码（200=成功，400=参数错误，401=未登录，500=服务器错误）
    "msg": "操作成功",   # 提示信息
    "data": {...}       # 实际数据
})
```

### 课堂任务：用postman测试以下接口

1. POST 请求 `http://127.0.0.1:5001/api/register` 发送 `{"username": "astronaut_01"}
2. GET 请求 `http://127.0.0.1:5001/api/users?page=1&limit=5` 查看返回的分页数据（模拟10条数据）

```python
import json
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# 数据文件路径（与脚本同目录）
DATA_FILE = os.path.join(os.path.dirname(__file__), "users.json")

# 加载已有用户（从 JSON 文件）
def load_users():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# 保存用户到 JSON 文件
def save_users(users):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

users_db = load_users()

@app.route('/api/register', methods=['POST'])
def register():
    """
    注册接口
    Postman: POST http://127.0.0.1:5001/api/register
    Body (raw JSON): {"username": "new_user"}
    """
    data = request.get_json()
    username = data.get('username')
    if not username:
        return jsonify({"code": 400, "msg": "缺少 username"}), 400

    user = {"id": len(users_db) + 1, "username": username}
    users_db.append(user)
    save_users(users_db)  # 注册后持久化到 JSON 文件
    return jsonify({"code": 200, "msg": "注册成功", "data": user}), 200

@app.route('/api/users', methods=['GET'])
def get_users():
    """
    获取用户列表（分页）
    Postman: GET http://127.0.0.1:5001/api/users?page=1&limit=5
    """
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))

    start = (page - 1) * limit
    end = start + limit
    page_data = users_db[start:end]

    return jsonify({
        "code": 200,
        "msg": "获取成功",
        "data": page_data,
        "total": len(users_db),
        "page": page,
        "limit": limit
    })

if __name__ == '__main__':
    app.run(host="127.0.0.1", port=5001, debug=True)
```

<style> table { border-collapse: collapse; width: 100%; } th, td { border: 1px solid #ccc; padding: 8px; text-align: left; } </style>

### 2.3  request.form

```python
@app.route('/api/submit-form', methods=['POST'])
def submit_form():
    """
    表单提交接口
    Postman: POST http://127.0.0.1:5001/api/submit-form
    Body (form-data): username=test_user, email=test@example.com
    """
    username = request.form.get('username')
    email = request.form.get('email')

    if not username:
        return jsonify({"code": 400, "msg": "用户名不能为空"}), 400

    return jsonify({"code": 200, "msg": f"收到表单数据：用户={username}, 邮箱={email}"})
```



### 2.4 Flask获取参数的方式

| 获取方式                 | 取哪里的数据                | 适用场景                                           |
| -------------------- | --------------------- | ---------------------------------------------- |
| `request.args.get()` | URL 中 `?key=val` 查询参数 | GET/POST 都能用                                   |
| 路由 `<变量名>`           | URL 路径片段 `/user/1`    | GET/POST 通用                                    |
| `request.form.get()` | 请求体 表单数据              | POST，form-data / urlencoded                    |
| `request.get_json()` | 请求体 JSON 数据           | POST，Header 携带 `Content-Type:application/json` |



## 模块三：用户认证系统（注册/登录/登出）

### 1.密码安全：绝对不能明文存储！

```
user_db = {"admin":"123456"}
```

使用 `werkzeug.security` 提供的哈希函数。

```python
from werkzeug.security import generate_password_hash, check_password_hash

# 1. 注册时：对密码进行哈希加密
password_hash = generate_password_hash("123456")
# 结果类似：'scrypt:32768:8:1$xxx$yyy...'（不可逆）

# 2. 登录时：比对密码
is_correct = check_password_hash(password_hash, "123456")  # 返回 True 或 False
```

为什么不能明文存储？

- 数据库一旦暴露，全部用户密码直接暴露

- 很多用户在多个网站都是相同的密码，一个网站泄露，所有网站都泄露

- 哈希单向加密的，无法反推出原始密码

### 2.Session保持登录状态？

Session是什么？

http协议无状态的，session记住用户的身份的一种机制

Flask用session，共工作原理：

- 用户登录后，服务器会自动生成一个Session数据（比如{“username”：“admin”}）

- 服务器用secret_key对这个数据进行加密签名，生成一个cooki给到浏览器

- 浏览器之后的每次请求都会自动带上这个cookie

- 服务器解密cookie，放行，数据互通

**secret_key**

```
app.secret_key = secrets.token_hex(16)  # 生成一个 32 位的随机密钥
```

Session 的常见操作

```pythobn
from flask import session

# 存储数据
session['username'] = 'admin'
session['role'] = 'admin'

# 读取数据
username = session.get('username')  # 如果不存在返回 None，不会报错

# 删除数据
session.pop('username', None)

# 清空所有 Session
session.clear()
```

## 模块四：博客点赞互动实例

#### 1.RESRful API设计原则

**REST**（Representational State Transfer）是一种 API 设计风格，核心思想是：

> **用 URL 表示资源，用 HTTP 方法表示操作**

| HTTP 方法 | URL            | 含义              | 数据库操作  |
| ------- | -------------- | --------------- | ------ |
| GET     | `/api/posts`   | 获取所有博客列表        | SELECT |
| POST    | `/api/posts`   | 发布新博客           | INSERT |
| GET     | `/api/posts/1` | 获取 ID 为 1 的博客   | SELECT |
| PUT     | `/api/posts/1` | 完整更新 ID 为 1 的博客 | UPDATE |
| PATCH   | `/api/posts/1` | 部分更新 ID 为 1 的博客 | UPDATE |
| DELETE  | `/api/posts/1` | 删除 ID 为 1 的博客   | DELETE |

### 2. 装饰器：@login_required

登录装饰器的实现：

```python
from functools import wraps

def login_required(f):
    @wraps(f)  # 保留原函数的元信息（如函数名、文档字符串）
    def decorated(*args, **kwargs):
        if 'username' not in session:
            return jsonify({"code": 401, "msg": "请先登录"}), 401
        return f(*args, **kwargs)  # 执行原函数
    return decorated
```

```python
@app.route('/api/posts', methods=['POST'])
@login_required  # 加上这个，访问这个接口就必须先登录
def create_post():
    # 只有登录用户才能执行这里的代码
    pass
```

### 3.项目实战：完整博客系统

```python

# 用户登录与注册接口

from flask import Flask, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

app = Flask(__name__)
app.json.ensure_ascii = False 
# 配置会话密钥
app.secret_key = secrets.token_hex(16)

#模拟数据库
users_db = {}

@app.route("/auth/register", methods=['POST'])
def register():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"code": 400, "msg": "请提供 username 和 password"}), 400
    
    username = data['username']
    password = data['password']
    
    if username in users_db:
        return jsonify({"code": 400, "msg": "用户名已存在"}), 400
    
    # 核心安全操作：对密码进行哈希加盐存储
    password_hash = generate_password_hash(password)
    users_db[username] = {
        "password_hash": password_hash,
        "role": "user",
        "status": "active"
    }
    return jsonify({"code": 200, "msg": "注册成功"})


@app.route("/auth/login", methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"code": 400, "msg": "请提供 username 和 password"}), 400
    
    username = data['username']
    password = data['password']
    
    if username not in users_db:
        return jsonify({"code": 401, "msg": "用户名不存在"}), 401
    
    #核心验证：对比铭文密码与存储的哈希值是否一致
    if not check_password_hash(users_db[username]["password_hash"], password):
        return jsonify({"code": 401, "msg": "密码错误"}), 401    
    # 登录成功，设置会话，将用户名和其他相关信息存入session
    session["username"] = username
    session["role"] = users_db[username]["role"]
    return jsonify({"code": 200, "msg": "登录成功", "username": username, "role": session["role"]})
    
    
@app.route("/auth/profile")
def profile():
    if 'username' not in session:
        return jsonify({"code": 401, "msg": "未登录"}), 401
    return jsonify({
        "code": 200,
        "data": {
            "username": session['username'],
            "role": session.get('role', 'user')
        }
    })

    
@app.route("/auth/logout", methods=['POST'])
def logout():
    session.clear()
    return jsonify({"code": 200, "msg": "已成功推出登录"})


if __name__ == '__main__':
    app.run(host="127.0.0.1", port=5003, debug=True)__name__ == '__main__':
    app.run(host="127.0.0.1", port=5003, debug=True)
```



# 📦 任务：技术公司官方网站与内容管理系统 (CMS)

### 📊 项目描述

某科技初创公司需要一个动态官网，用于展示公司简介、新闻公告，并提供后台内容管理功能。

### 🎯 任务要求

请独立编写 `app_company_cms.py`，实现以下功能：

1. **前台展示接口**：
   
   * `GET /`：展示公司首页（公司简介、最新 3 条新闻）。
   * `GET /api/news`：获取新闻列表（支持按发布时间倒序）。
   * `GET /api/news/<id>`：获取新闻详情。

2. **后台管理接口（需管理员权限）**：
   
   * 管理员账号预设：`admin / admin123`。
   * `POST /admin/news`：发布新新闻（字段：`title`, `content`, `category`）。
   * `DELETE /admin/news/<id>`：删除指定新闻。
   * 必须实现登录校验装饰器，非 `admin` 角色访问后台接口返回 `403 Forbidden`。

3. **数据持久化（可选挑战）**：
   
   * 使用 `sqlite3` 或 `SQLAlchemy` 将新闻数据存入本地文件 `cms.db`，替代内存字典，确保重启服务器后数据不丢失。

4. **测试提交**：
   
   * 提交完整的 `.py` 文件。
   * 附带 Postman 或 Curl 测试截图（包含成功登录、发布新闻、前台获取新闻的完整链路）。
   * 测试接口全部无误后，让ai生成前端页面，完成一个完整的CMS。

* * *

## 📝 提交要求

1. 所有代码必须包含详细的中文注释。
2. 运行前请确保已通过 `pip install flask requests` 安装依赖。
   
   


