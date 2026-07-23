# flask4_博客发布与点赞.py
# 模块四：博客 CRUD 与点赞互动

from flask import Flask, request, jsonify, session
from datetime import datetime
import secrets
from functools import wraps

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# 模拟数据库
posts_db = {}
next_id = 1

@app.route('/login', methods=['POST'])
def login_temp():
    """
    📥 Postman 测试：临时登录（用于快速测试）
    --------------------------------------------------
    Method: POST
    URL: http://127.0.0.1:5003/login
    Expected Response:
    {
        "code": 200,
        "msg": "临时登录成功 (user: admin)"
    }
    --------------------------------------------------
    说明：此接口直接设置 session，无需密码，专用于本模块功能测试。
    登录后，Postman 会自动保存 Cookie，后续请求即可携带身份。
    """
    session['username'] = 'admin'
    session['role'] = 'user'
    return jsonify({"code": 200, "msg": "临时登录成功 (user: admin)"})

def login_required(f):
    """登录校验装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            return jsonify({"code": 401, "msg": "请先登录"}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/api/posts', methods=['POST'])
@login_required
def create_post():
    """
     Postman 测试：发布新博客（需登录）
    --------------------------------------------------
    Method: POST
    URL: http://127.0.0.1:5003/api/posts
    Headers: 
      - Content-Type: application/json
      - Cookie: (Postman 会自动携带，前提是先完成登录)
    Body (raw -> JSON):
    {
        "title": "火星基地的第一次日落",
        "content": "今天的夕阳非常壮观，红色的天空美得令人窒息。"
    }
    Expected Response (成功):
    {
        "code": 200,
        "msg": "发布成功",
        "data": {
            "id": 1,
            "title": "火星基地的第一次日落",
            "content": "今天的夕阳非常壮观...",
            "author": "astronaut1",
            "created_at": "2026-07-19 15:30:00",
            "likes": 0,
            "liked_by": []
        }
    }
    Expected Response (未登录):
    {
        "code": 401,
        "msg": "请先登录"
    }
    --------------------------------------------------
    前置条件：先调用 POST /login 进行临时登录（无需密码），
    让 Postman 保存 Session Cookie 后即可访问。
    --------------------------------------------------
    说明：@login_required 装饰器会检查 session 中是否有 username
    """
    global next_id
    data = request.get_json()
    if not data.get('title') or not data.get('content'):
        return jsonify({"code": 400, "msg": "标题和内容不能为空"}), 400
        
    post = {
        "id": next_id,
        "title": data['title'],
        "content": data['content'],
        "author": session['username'],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "likes": 0,
        "liked_by": []  # 记录点赞用户，防止重复点赞
    }
    posts_db[next_id] = post
    next_id += 1
    return jsonify({"code": 200, "msg": "发布成功", "data": post}), 201

@app.route('/api/posts', methods=['GET'])
def list_posts():
    """
    📥 Postman 测试：获取博客列表
    --------------------------------------------------
    Method: GET
    URL: http://127.0.0.1:5003/api/posts
    Expected Response:
    {
        "code": 200,
        "data": [
            {
                "id": 2,
                "title": "...",
                ...
            },
            {
                "id": 1,
                "title": "...",
                ...
            }
        ]
    }
    --------------------------------------------------
    说明：此接口无需登录，返回所有博客（按时间倒序）
    """
    sorted_posts = sorted(posts_db.values(), key=lambda x: x['id'], reverse=True)
    return jsonify({"code": 200, "data": sorted_posts})

@app.route('/api/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    """
    📥 Postman 测试：获取单篇博客详情
    --------------------------------------------------
    Method: GET
    URL: http://127.0.0.1:5003/api/posts/1
    替换 1 为具体的博客 ID
    Expected Response (成功):
    {
        "code": 200,
        "data": {
            "id": 1,
            "title": "...",
            ...
        }
    }
    Expected Response (博客不存在):
    {
        "code": 404,
        "msg": "博客不存在"
    }
    """
    if post_id not in posts_db:
        return jsonify({"code": 404, "msg": "博客不存在"}), 404
    return jsonify({"code": 200, "data": posts_db[post_id]})

@app.route('/api/posts/<int:post_id>/like', methods=['POST'])
@login_required
def like_post(post_id):
    """
    📥 Postman 测试：点赞博客（需登录）
    --------------------------------------------------
    Method: POST
    URL: http://127.0.0.1:5003/api/posts/1/like
    替换 1 为具体的博客 ID
    Expected Response (成功):
    {
        "code": 200,
        "likes": 1,
        "msg": "点赞成功"
    }
    Expected Response (重复点赞):
    {
        "code": 400,
        "msg": "您已经点赞过该博客了",
        "likes": 1
    }
    --------------------------------------------------
    前置条件：先调用 POST /login 进行临时登录，
    防止重复点赞逻辑依赖 session 中的 username。
    --------------------------------------------------
    说明：通过 liked_by 列表记录已点赞用户，防止同一用户重复点赞
    """
    if post_id not in posts_db:
        return jsonify({"code": 404, "msg": "博客不存在"}), 404
    
    post = posts_db[post_id]
    current_user = session['username']
    
    if current_user in post['liked_by']:
        return jsonify({"code": 400, "msg": "您已经点赞过该博客了", "likes": post['likes']}), 400
    
    post['likes'] += 1
    post['liked_by'].append(current_user)
    return jsonify({"code": 200, "likes": post['likes'], "msg": "点赞成功"})

@app.route('/api/posts/<int:post_id>/comment', methods=['POST'])
@login_required
def comment_post(post_id):
    """
    📥 Postman 测试：发表评论（需登录）
    --------------------------------------------------
    Method: POST
    URL: http://127.0.0.1:5003/api/posts/1/comment
    Headers: Content-Type: application/json
    Body (raw -> JSON):
    {
        "text": "写得真好！"
    }
    Expected Response:
    {
        "code": 200,
        "msg": "评论发布成功",
        "comment": "写得真好！"
    }
    --------------------------------------------------
    前置条件：先调用 POST /login 进行临时登录。
    """
    if post_id not in posts_db:
        return jsonify({"code": 404, "msg": "博客不存在"}), 404
    
    data = request.get_json()
    if not data.get('text'):
        return jsonify({"code": 400, "msg": "评论内容不能为空"}), 400
        
    return jsonify({"code": 200, "msg": "评论发布成功", "comment": data['text']})

# 测试入口
if __name__ == '__main__':
    print("📝 博客服务器启动于: http://127.0.0.1:5003")
    print("📝 测试流程:")
    print("   1. POST /login              → 临时登录 (无需密码，Postman 自动保存 Cookie)")
    print("   2. POST /api/posts          → 发布新博客")
    print("   3. GET  /api/posts          → 查看博客列表")
    print("   4. POST /api/posts/1/like   → 点赞 ID 为 1 的博客")
    app.run(debug=True, port=5003)
