import pymysql

DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '123456',
    'database': 'test_db',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_connection():
    return pymysql.connect(**DB_CONFIG)

# 1. 增
def add_user(username, age, email):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "INSERT INTO users (username, age, email) VALUES (%s, %s, %s)"
            cursor.execute(sql, (username, age, email))
            conn.commit()  
            print(f"成功插入用户，新增 ID: {cursor.lastrowid}")
    except Exception as e:
        conn.rollback()  
        print(f"新增失败: {e}")
    finally:
        conn.close()

# 2. 查
def get_all_users():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT id, username, age, email, created_at FROM users"
            cursor.execute(sql)
            result = cursor.fetchall() 
            return result
    finally:
        conn.close()

def get_user_by_id(user_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM users WHERE id = %s"
            cursor.execute(sql, (user_id,))
            return cursor.fetchone()  
    finally:
        conn.close()

# 3. 改
def update_user_email(user_id, new_email):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "UPDATE users SET email = %s WHERE id = %s"
            affected_rows = cursor.execute(sql, (new_email, user_id))
            conn.commit()
            print(f"更新成功，影响行数: {affected_rows}")
    except Exception as e:
        conn.rollback()
        print(f"更新失败: {e}")
    finally:
        conn.close()

# 4. 删
def delete_user(user_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "DELETE FROM users WHERE id = %s"
            affected_rows = cursor.execute(sql, (user_id,))
            conn.commit()
            print(f"删除成功，影响行数: {affected_rows}")
    except Exception as e:
        conn.rollback()
        print(f"删除失败: {e}")
    finally:
        conn.close()


if __name__ == '__main__':
    print("1. 插入数据")
    add_user("a", 25, "a.com")
    add_user("b", 30, "b.com")

    print("\2. 查询所有数据")
    users = get_all_users()
    for u in users:
        print(u)

    print("3. 修改数据")
    if users:
        first_id = users[0]['id']
        update_user_email(first_id, "a.com")
        print("修改后：", get_user_by_id(first_id))

    print("4. 删除数据")
    if len(users) > 1:
        second_id = users[1]['id']
        delete_user(second_id)
        
    print("\n--- 最终用户列表 ---")
    print(get_all_users())
