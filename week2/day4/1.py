'''
课堂任务：用postman测试以下接口

1. POST 请求 `http://127.0.0.1:5001/api/register` 发送 `{"username": "astronaut_01"}
2. GET 请求 `http://127.0.0.1:5001/api/users?page=1&limit=5` 查看返回的分页数据（模拟10条数据）
'''

from flask import Flask, request, jsonify

app = Flask(__name__)

# 模拟数据库
users_db = []


@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = data.get("username")

    if not username:
        return jsonify({"error": "username is required"}), 400

    user = {
        "username": username,
    }
    users_db.append(user)

    return jsonify({"message": "register success", "user": user}), 201


@app.route("/api/users", methods=["GET"])
def get_users():
    page = request.args.get("page", default=1, type=int)
    limit = request.args.get("limit", default=5, type=int)

    if page < 1 or limit < 1:
        return jsonify({"error": "page and limit must be positive integers"}), 400

    start = (page - 1) * limit
    end = start + limit
    users = users_db[start:end]

    return jsonify(
        {
            "page": page,
            "limit": limit,
            "total": len(users_db),
            "users": users,
        }
    )




if __name__ == '__main__':
    app.run(debug=True, port=5001)
