from flask import Flask, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

user_db = {}


@app.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"code": 400, "message": "用户名和密码不能为空"}), 400

    if username in user_db:
        return jsonify({"code": 409, "message": "用户已存在"}), 409

    user_db[username] = {
        "username": username,
        "password_hash": generate_password_hash(password),
    }
    return jsonify({"code": 200, "message": "注册成功"}), 200


@app.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    user = user_db.get(username)
    if not user or not check_password_hash(user["password_hash"], str(password)):
        return jsonify({"code": 401, "message": "用户名或密码错误"}), 401

    session["username"] = username
    return jsonify({"code": 200, "message": "登录成功"}), 200


@app.route("/auth/profile", methods=["GET"])
def profile():
    username = session.get("username")
    if not username:
        return jsonify({"code": 401, "message": "请先登录"}), 401

    return jsonify({"code": 200, "message": "已登录", "username": username}), 200


@app.route("/auth/logout", methods=["POST"])
def logout():
    session.pop("username", None)
    return jsonify({"code": 200, "message": "退出成功"}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5002)
