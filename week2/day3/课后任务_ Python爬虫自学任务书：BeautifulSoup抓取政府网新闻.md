# Python爬虫自学任务书：BeautifulSoup抓取政府网新闻
## 一、任务信息
1. 依托讲义：HTTP协议、requests、SQLAlchemy、XPath解析
2. 技术栈：requests + BeautifulSoup4 + lxml + SQLite
3. 目标网址：https://www.gov.cn/toutiao/liebiao/
4. 核心学习重点：自学BeautifulSoup，回顾巩固CSS选择器语法

## 二、学习目标
1. 自主学习BeautifulSoup基础用法，掌握页面解析流程；
2. 复习CSS选择器语法，使用CSS选择器提取网页数据；
3. 结合课堂requests知识，写出合规防反爬爬虫；
4. 复用SQLAlchemy代码，将新闻数据存入本地SQLite数据库。

## 三、前置基础（课堂已全部讲解）
requests请求、请求头伪装、分页循环、SQLAlchemy操作SQLite、XPath基础

## 四、环境安装
```bash
pip install requests beautifulsoup4 lxml sqlalchemy
```

## 五、基础功能要求（必须完成）
### 1. 数据库部分（直接复用讲义代码）
1. 生成`gov_news.db`，数据表`gov_news`；
2. 字段：自增id、新闻标题title、发布时间publish_time、新闻链接link（链接唯一）；
3. 写入数据失败自动回滚，捕获数据库异常。

### 2. 爬虫请求配置（强制，防止触发反爬）
1. 配置完整浏览器headers（UA、Accept、Referer、中文语言）；
2. 请求超时5秒；
3. 每页抓取后随机休眠2~4秒；
4. 判断403状态码，出现则提示终止抓取。

### 3. BeautifulSoup核心自学内容（本次任务重点）
1. 使用`lxml`解析器创建soup对象；
2. 熟练使用CSS选择器：
   - `select()`：匹配多条数据
   - `select_one()`：匹配单条标签
3. 数据提取方法：
   - `.get_text(strip=True)` 提取干净文本
   - 标签["属性名"] 提取链接、图片等属性
4. 拼接相对链接为完整网址。

### 4. 分页抓取规则
1. 封装函数`crawl_page(page_num)`实现单页抓取入库；
2. 仅循环抓取1~10页，禁止抓取全部435页；
3. 增加异常捕获，单页报错不中断整体程序。

## 六、硬性合规要求
1. 仅限前10页测试，不允许全量爬取；
2. 不得删除延时、请求头伪装代码；
3. 仅用于课程学习，禁止商用、批量分发数据；
4. 只能单线程串行抓取，不使用多线程/代理IP。

## 七、代码规范
1. 代码分段注释清晰，分为数据库、请求配置、抓取函数、主程序；
2. 打印每页抓取日志，方便查看运行进度；
3. 所有异常捕获并打印错误信息。

## 八、拓展选做任务（自愿完成）
1. 制作简易交互式菜单，支持指定单页抓取/批量抓取；
2. 将数据库数据导出为csv文件；
3. 对比练习：同一页面分别用XPath和BeautifulSoup两种方式解析，简单记录两者区别；
4. 增加空值过滤，标题/时间为空的数据不存入数据库。

## 九、提交内容
1. 完整可运行py源代码；
2. 生成的`gov_news.db`数据库文件；
3. 简短说明：自学BS4学到的核心语法、抓取时遇到的反爬问题及解决办法。

## 附：基础参考模板
```python
import requests
import time
import random
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

# 1. 数据库模型（讲义复用）
engine = create_engine("sqlite:///gov_news.db", echo=False)
Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class GovNews(Base):
    __tablename__ = "gov_news"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500))
    publish_time = Column(String(30))
    link = Column(String(800), unique=True)

Base.metadata.create_all(bind=engine)

# 2. 防反爬请求头
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://www.gov.cn/"
}

def crawl_page(page_num):
    url = f"https://www.gov.cn/toutiao/liebiao/?page={page_num}"
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 403:
            print(f"第{page_num}页访问受限，触发反爬")
            return False
        resp.encoding = "utf-8"
        # BS4核心自学代码
        soup = BeautifulSoup(resp.text, "lxml")
        news_list = soup.select("自行填写新闻列表CSS选择器")
        db = SessionLocal()
        for item in news_list:
            title = item.select_one("a").get_text(strip=True)
            href = item.select_one("a")["href"]
            full_link = "https://www.gov.cn" + href
            pub_time = item.select_one("span").get_text(strip=True)
            db.add(GovNews(title=title, publish_time=pub_time, link=full_link))
        db.commit()
        db.close()
        print(f"第{page_num}页抓取完成")
        return True
    except Exception as e:
        print(f"第{page_num}页异常：{e}")
        return False

if __name__ == "__main__":
    # 仅抓取1-10页
    for page in range(1, 11):
        crawl_page(page)
        time.sleep(random.uniform(2, 4))
    print("抓取全部完成")
```