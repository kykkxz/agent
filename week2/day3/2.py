'''
BeautifulSoup抓取政府网新闻

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

### 5. 控制台交互
使用了rich优化显示
'''
import random
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.panel import Panel
from rich.prompt import IntPrompt, Prompt
from rich.table import Table
from sqlalchemy import Column, Integer, String, Text, create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session

'''
全局变量定义
'''
BASE_URL = "https://www.gov.cn/toutiao/liebiao/"
DB_URL = "sqlite:///gov_news.db"
MAX_PAGES = 5
TIMEOUT_SECONDS = 20
MIN_SLEEP_SECONDS = 2
MAX_SLEEP_SECONDS = 4
ENGINE = create_engine(DB_URL)
console = Console()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
        "image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.gov.cn/",
    "Host": "www.gov.cn",
    "Connection": "keep-alive",
    "Cache-Control": "max-age=0",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}

class Base(DeclarativeBase):
    '''
    sqlalchemy基类定义
    '''
    pass


class GovNews(Base):
    '''
    新闻数据表定义
    '''
    __tablename__ = "gov_news"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    publish_time = Column(String(30), nullable=False)
    link = Column(Text, nullable=False, unique=True)

    def __repr__(self):
        return f"<GovNews(id={self.id}, title={self.title}, link={self.link[:30]}...)>"


class NewsItem:
    '''
    新闻数据表py类定义
    '''
    def __init__(self, title, publish_time, link):
        self.title = title
        self.publish_time = publish_time
        self.link = link


def init_db():
    '''
    sqlalchemy创建表
    '''
    Base.metadata.create_all(ENGINE)


def build_page_url(page_num):
    '''
    拼接url
    '''
    if page_num == 1:
        return f"{BASE_URL}home.htm"
    return f"{BASE_URL}home_{page_num - 1}.htm"


def fetch_page(page_num):
    '''
    单页请求
    '''
    url = build_page_url(page_num)

    try:
        return requests.get(url, headers=HEADERS, timeout=TIMEOUT_SECONDS)
    except requests.exceptions.RequestException as exc:
        console.print(f"[red]第{page_num}页请求失败：{exc}[/red]")
        return None


def extract_news_html(html):
    '''
    html初步解析
    '''
    main_start = html.find('<div class="main">')
    if main_start == -1:
        return html
    return html[main_start:]


def parse_news(html, base_url):
    '''
    html中解析具体的新闻信息
    '''
    soup = BeautifulSoup(extract_news_html(html), "lxml")
    items = []
    seen_links = set()

    for item in soup.select(".news_box .list_2 li"):
        link_tag = item.select_one("h4 a[href]")
        date_tag = item.select_one("span.date")
        if not link_tag or not date_tag:
            continue

        title = link_tag.get_text(strip=True)
        href = str(link_tag["href"])
        full_link = urljoin(base_url, href)
        publish_time = date_tag.get_text(strip=True)

        if not title or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", publish_time) or full_link in seen_links:
            continue

        seen_links.add(full_link)
        items.append(
            NewsItem(
                title=title,
                publish_time=publish_time,
                link=full_link,
            )
        )

    return items


def save_news(items):
    '''
    保存解析的新闻到数据库
    '''
    saved_count = 0

    with Session(ENGINE) as session:
        try:
            for item in items:
                exists = session.scalar(select(GovNews).where(GovNews.link == item.link))
                if exists:
                    continue

                session.add(
                    GovNews(
                        title=item.title,
                        publish_time=item.publish_time,
                        link=item.link,
                    )
                )
                saved_count += 1

            session.commit()
        except SQLAlchemyError as exc:
            session.rollback()
            console.print(f"[red]数据库保存失败，已回滚：{exc}[/red]")
            return 0

    return saved_count


def crawl_page(page_num):
    '''
    完整单页抓取流程封装
    '''
    response = fetch_page(page_num)
    if response is None:
        return True

    console.print(f"第{page_num}页状态码：[cyan]{response.status_code}[/cyan]")
    if response.status_code == 403:
        console.print("[red]检测到403访问受限，终止抓取。[/red]")
        return False

    if response.status_code != 200:
        console.print(f"[yellow]第{page_num}页HTTP错误：{response.status_code}[/yellow]")
        return True

    try:
        response.encoding = response.apparent_encoding or "utf-8"
        items = parse_news(response.text, response.url)
        saved_count = save_news(items)
        console.print(f"[green]第{page_num}页抓取完成：解析{len(items)}条，新增{saved_count}条[/green]")
    except Exception as exc:
        console.print(f"[red]第{page_num}页解析或保存异常：{exc}[/red]")

    return True


def sleep_after_page(page_num):
    '''
    停顿
    '''
    sleep_seconds = random.uniform(MIN_SLEEP_SECONDS, MAX_SLEEP_SECONDS)
    console.print(f"第{page_num}页抓取后随机休眠 [cyan]{sleep_seconds:.1f}[/cyan] 秒")
    time.sleep(sleep_seconds)


def input_page(prompt_text):
    '''
    自定义输入抓取页码
    '''
    while True:
        page_num = IntPrompt.ask(prompt_text)
        if 1 <= page_num <= MAX_PAGES:
            return page_num
        console.print(f"[yellow]请输入1到{MAX_PAGES}之间的页码。[/yellow]")


def crawl_pages(start_page, end_page):
    '''
    多页抓取
    '''
    if start_page > end_page:
        start_page, end_page = end_page, start_page

    for page_num in range(start_page, end_page + 1):
        if not crawl_page(page_num):
            break

        if page_num < end_page:
            sleep_after_page(page_num)

    console.print("[green]抓取结束[/green]")


def show_news():
    '''
    数据库预览
    '''
    limit = IntPrompt.ask("查看最近多少条数据", default=20)

    with Session(ENGINE) as session:
        rows = session.scalars(
            select(GovNews).order_by(GovNews.id).limit(limit)
        ).all()

    if not rows:
        console.print("[yellow]数据库暂无内容。[/yellow]")
        return

    table = Table(title=f"gov_news 最近 {len(rows)} 条")
    table.add_column("ID", justify="right")
    table.add_column("发布时间")
    table.add_column("标题", overflow="fold")
    table.add_column("链接", overflow="fold")

    for row in rows:
        table.add_row(str(row.id), str(row.publish_time), str(row.title), str(row.link))

    console.print(table)


def show_menu():
    '''
    控制台交互
    '''
    console.print(
        Panel(
            "1. 指定单页抓取\n"
            "2. 批量抓取\n"
            "3. 查看数据库内容\n"
            "0. 退出",
            title="政府网新闻爬虫",
            border_style="cyan",
        )
    )
    return Prompt.ask("请选择功能", choices=["1", "2", "3", "0"], default="1")


def main():
    try:
        init_db()
    except SQLAlchemyError as exc:
        console.print(f"[red]数据库初始化失败：{exc}[/red]")
        return 1

    while True:
        choice = show_menu()

        if choice == "1":
            page_num = input_page("请输入要抓取的页码")
            crawl_page(page_num)
        elif choice == "2":
            start_page = input_page("请输入起始页码")
            end_page = input_page("请输入结束页码")
            crawl_pages(start_page, end_page)
        elif choice == "3":
            show_news()
        else:
            console.print("[cyan]已退出。[/cyan]")
            break

    return 0


if __name__ == "__main__":
    main()
