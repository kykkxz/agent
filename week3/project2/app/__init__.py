from flask import Flask, send_from_directory
from werkzeug.exceptions import HTTPException

from app.api.v1 import register_blueprints
from app.core.database import Base, close_db, engine
from app.core.response import BizException, error_response
from app.core.security import hash_password
from app.models import PromptTemplate, User

DEFAULT_PROMPT = """你是保险营销文案专家。请根据以下客户画像生成一封个性化车险营销邮件。
客户画像：性别{gender}，年龄{age}岁，{driving_license}驾照，车龄{vehicle_age}，车辆{vehicle_damage}，年保费{annual_premium}元。
要求：语气专业有温度，突出该客户画像的痛点与利益，包含行动号召(CTA)。
仅返回严格 JSON，格式：{{\"subject\":\"邮件主题\",\"content\":\"HTML格式正文\"}}"""


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config["MAX_CONTENT_LENGTH"] = 30 * 1024 * 1024
    register_blueprints(app)
    app.teardown_appcontext(close_db)

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder or "static", "index.html")

    @app.errorhandler(BizException)
    def handle_business_error(error: BizException):
        return error_response(error.code, error.message, error.status_code)

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        return error_response(1001, error.description, error.code or 400)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        app.logger.exception("Unhandled application error", exc_info=error)
        return error_response(5000, "服务器内部错误", 500)

    with app.app_context():
        Base.metadata.create_all(bind=engine)
        from app.core.database import SessionLocal

        with SessionLocal() as session:
            if session.query(User).filter_by(username="admin").first() is None:
                session.add(
                    User(username="admin", password_hash=hash_password("admin123"), role="admin")
                )
            if session.query(PromptTemplate).filter_by(is_active=True).first() is None:
                session.add(PromptTemplate(name="default", content=DEFAULT_PROMPT, is_active=True))
            session.commit()
    return app
