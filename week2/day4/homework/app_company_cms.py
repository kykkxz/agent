'''
 📦 任务：技术公司官方网站与内容管理系统 (CMS)

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
'''
from datetime import datetime
from functools import wraps
import secrets

from flask import Flask, jsonify, render_template, request, session
from flask.json.provider import DefaultJSONProvider
from sqlalchemy import Column, Integer, String, Text, create_engine, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session

'''
初始化全局变量
'''
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
if isinstance(app.json, DefaultJSONProvider):
    app.json.ensure_ascii = False

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
DB_URL = "sqlite:///cms.db"
ENGINE = create_engine(DB_URL)

'''
sqlalchemy基类定义
'''
class Base(DeclarativeBase):
    pass

class News(Base):
    '''
    新闻表定义
    '''
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)
    published_at = Column(String(30), nullable=False)
    author = Column(String(50), nullable=False)


company_info = {
    "name": "网讯创智",
    "description": "四川网讯创智数字产业发展有限公司是自贡政府、百度、四川广电共同打造之人工智能(西南)产训基地的专职项目运营公司",
}

DEFAULT_NEWS = [
    {
        "title": "公司完成新一轮产品升级",
        "content": "携手抖音火山引擎、巨量引擎、绵阳安州政府、品高软件，推动抖音“双擎计划”在四川的深度落地，共同打造“绵阳数字经济产业加速器”，并在绵阳花荄落地6000平米数字化产业基地",
        "category": "公司动态",
        "published_at": "2021年",
        "author": "admin",
    },
    {
        "title": "数字化产业基地",
        "content": "携手抖音火山引擎、内江高新区政府、内江投资控股集团共同打造“成渝数字经济产业加速器”，并在高新大厦落地2800平米的数字化产业基地；",
        "category": "产品新闻",
        "published_at": "2022年",
        "author": "admin",
    },
    {
        "title": "政企合作",
        "content": "携手抖音火山引擎、资阳市委宣传部、资阳高新投资集团共同打造“融媒体数字生态加速器”，全面推进资阳融媒体改革与产业化落地的先行实践，并成为中宣部融媒体改革示范标杆；",
        "category": "合作新闻",
        "published_at": "2023年",
        "author": "admin",
    },
]


def init_db():
    '''
    初始化表
    '''
    Base.metadata.create_all(ENGINE)
    with Session(ENGINE) as db_session:
        exists = db_session.scalar(select(News.id).limit(1))
        if exists is not None:
            return

        for item in DEFAULT_NEWS:
            db_session.add(News(**item))
        db_session.commit()


def news_to_dict(news):
    '''
    解析新闻信息
    '''
    return {
        "id": news.id,
        "title": news.title,
        "content": news.content,
        "category": news.category,
        "published_at": news.published_at,
        "author": news.author,
    }


def wants_html():
    '''
    判断浏览器访问还是终端访问
    '''
    return "text/html" in request.headers.get("Accept", "")


def admin_required(f):
    '''
    登录校验装饰器
    '''
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "admin":
            return jsonify({"code": 403, "msg": "Forbidden"}), 403
        return f(*args, **kwargs)

    return decorated


init_db()


@app.route("/", methods=["GET"])
def home():
    '''
    `GET /`：展示公司首页（公司简介、最新 3 条新闻）
    '''
    with Session(ENGINE) as db_session:
        latest_news = db_session.scalars(
            select(News).order_by(News.published_at.desc()).limit(3)
        ).all()
        news_count = db_session.scalar(select(func.count()).select_from(News))

    latest_news_data = [news_to_dict(news) for news in latest_news]

    '''
    如果是浏览器访问就使用render_template
    '''
    if wants_html():
        return render_template(
            "index.html",
            company=company_info,
            latest_news=latest_news_data,
            news_count=news_count,
        )

    return jsonify(
        {
            "code": 200,
            "data": {
                "company": company_info,
                "latest_news": latest_news_data,
            },
        }
    )


@app.route("/news/<int:news_id>", methods=["GET"])
def news_page(news_id):
    '''
    页面专用 → render_template
    `GET /api/news/<id>`：获取新闻详情。
    '''
    with Session(ENGINE) as db_session:
        news = db_session.get(News, news_id)
        if news is None:
            return render_template(
                "news_detail.html",
                company=company_info,
                news={
                    "title": "新闻不存在",
                    "category": "404",
                    "published_at": "",
                    "author": "",
                    "content": "你访问的新闻不存在或已被删除。",
                },
            ), 404

        return render_template("news_detail.html", company=company_info, news=news_to_dict(news))


@app.route("/admin", methods=["GET"])
def admin_page():
    '''
    页面专用 → render_template
    管理员界面
    '''
    return render_template(
        "admin.html",
        company=company_info,
        is_admin=session.get("role") == "admin",
    )


@app.route("/admin/login", methods=["POST"])
def admin_login():
    '''
    登录
    '''
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    if username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
        return jsonify({"code": 401, "msg": "管理员账号或密码错误"}), 401

    session["username"] = username
    session["role"] = "admin"
    return jsonify({"code": 200, "msg": "管理员登录成功"})


@app.route("/admin/logout", methods=["GET"])
def admin_logout():
    '''
    登出
    '''
    session.clear()
    return render_template("admin.html", company=company_info, is_admin=False)


@app.route("/api/news", methods=["GET"])
def list_news():
    '''
    新闻列表接口
    `GET /api/news`：获取新闻列表（支持按发布时间倒序）
    '''
    with Session(ENGINE) as db_session:
        news_list = db_session.scalars(
            select(News).order_by(News.published_at.desc())
        ).all()

    news_data = [news_to_dict(news) for news in news_list]

    if wants_html():
        return render_template(
            "news_list.html",
            company=company_info,
            news_list=news_data,
            news_count=len(news_data),
        )

    return jsonify({"code": 200, "data": news_data})


@app.route("/api/news/<int:news_id>", methods=["GET"])
def get_news(news_id):
    '''
    测试接口
    `GET /api/news/<id>`：获取新闻详情。
    '''
    with Session(ENGINE) as db_session:
        news = db_session.get(News, news_id)
        if news is None:
            return jsonify({"code": 404, "msg": "新闻不存在"}), 404

        return jsonify({"code": 200, "data": news_to_dict(news)})


@app.route("/admin/news", methods=["POST"])
@admin_required
def create_news():
    '''
    创建新闻
    '''
    data = request.get_json(silent=True) or {}
    title = data.get("title")
    content = data.get("content")
    category = data.get("category")

    if not title or not content or not category:
        return jsonify({"code": 400, "msg": "标题、内容和分类不能为空"}), 400

    with Session(ENGINE) as db_session:
        try:
            news = News(
                title=title,
                content=content,
                category=category,
                published_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                author=session["username"],
            )
            db_session.add(news)
            db_session.commit()
            db_session.refresh(news)
            return jsonify({"code": 200, "msg": "新闻发布成功", "data": news_to_dict(news)}), 201
        except SQLAlchemyError:
            db_session.rollback()
            return jsonify({"code": 500, "msg": "数据库保存失败"}), 500


@app.route("/admin/news/<int:news_id>", methods=["DELETE"])
@admin_required
def delete_news(news_id):
    '''
    删除新闻
    '''
    with Session(ENGINE) as db_session:
        news = db_session.get(News, news_id)
        if news is None:
            return jsonify({"code": 404, "msg": "新闻不存在"}), 404

        deleted_news = news_to_dict(news)
        try:
            db_session.delete(news)
            db_session.commit()
            return jsonify({"code": 200, "msg": "新闻删除成功", "data": deleted_news})
        except SQLAlchemyError:
            db_session.rollback()
            return jsonify({"code": 500, "msg": "数据库删除失败"}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5005)
