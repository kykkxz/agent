import pymysql

# 1. 数据库配置参数
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',           
    'password': '123456',   
    'database': 'test_db',    
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor    
}

def create_table():
    connection = None
    try:
        connection = pymysql.connect(**DB_CONFIG)
        
        with connection.cursor() as cursor:
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                age INT,
                email VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
            cursor.execute(create_table_sql)
            print("数据表 'users' 创建成功（或已存在）！")
            
    except Exception as e:
        print(f"创建数据表失败: {e}")
    finally:
        if connection:
            connection.close()

if __name__ == '__main__':
    create_table()
