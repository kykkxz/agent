"""
课堂任务：

1.http://quotes.toscrape.com/爬取 名言内容，作者，标签

2.try-excption 异常捕获

3.状态码，response.text

4.请求头，浏览器里面找，，timeout=5s

5.alchemy存在sqlite

6.控制界面
"""
import requests
from lxml import html as lxml_html
from sqlalchemy import Column, Integer, String, Text, UniqueConstraint, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session


BASE_URL = "http://quotes.toscrape.com/"
DB_URL = "sqlite:///quotes.db"
MAX_PAGES = 1
TIMEOUT_SECONDS = 5

HEADERS = {
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
        "image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7",
    "Cache-Control": "max-age=0",
    "Host": "quotes.toscrape.com",
    "Proxy-Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
    ),
}


class Base(DeclarativeBase):
    pass


class Quote(Base):
    __tablename__ = "quotes"
    __table_args__ = (UniqueConstraint("content", "author", name="uq_content_author"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(String(500), nullable=False)
    author = Column(String(100), nullable=False)
    tags = Column(Text, nullable=False)


class QuoteItem:
    def __init__(self, content: str, author: str, tags: list[str]):
        self.content = content
        self.author = author
        self.tags = tags


def get_engine(db_url: str) -> Engine:
    return create_engine(db_url)


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def fetch_page(url: str):
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT_SECONDS)
        print(f"URL: {url}")
        print(f"状态码: {response.status_code}")
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"请求失败: {url} -> {exc}") from exc

    return response


def parse_quotes(html: str, base_url: str) -> tuple[list[QuoteItem], str | None]:
    tree = lxml_html.fromstring(html)

    tree.make_links_absolute(base_url)

    items: list[QuoteItem] = []

    for quote_div in tree.cssselect("div.quote"):
        content = quote_div.cssselect("span.text")
        author = quote_div.cssselect("small.author")
        tags = [tag.text_content().strip() for tag in quote_div.cssselect("a.tag")]

        if not content or not author:
            continue

        items.append(
            QuoteItem(
                content=content[0].text_content().strip(),
                author=author[0].text_content().strip(),
                tags=tags,
            )
        )

    next_link = tree.cssselect("li.next > a")
    next_url = next_link[0].get("href") if next_link else None

    return items, next_url


def crawl_quotes(max_pages: int) -> list[QuoteItem]:
    all_items: list[QuoteItem] = []
    url: str | None = BASE_URL
    page_no = 1

    while url is not None and page_no <= max_pages:
        print(f"抓取第 {page_no} 页")
        response = fetch_page(url)
        items, next_path = parse_quotes(response.text, url)
        all_items.extend(items)
        print(f"解析完成: 本页 {len(items)} 条，累计 {len(all_items)} 条")
        url = next_path
        page_no += 1

    return all_items


def save_quotes(engine: Engine, items: list[QuoteItem]) -> int:
    init_db(engine)

    saved_count = 0
    try:
        with Session(engine) as session:
            for item in items:
                exists = session.scalar(
                    select(Quote).where(
                        Quote.content == item.content,
                        Quote.author == item.author,
                    )
                )
                if exists is not None:
                    continue

                session.add(
                    Quote(
                        content=item.content,
                        author=item.author,
                        tags=",".join(item.tags),
                    )
                )
                saved_count += 1

            session.commit()
    except SQLAlchemyError as exc:
        raise RuntimeError(f"数据库保存失败: {exc}") from exc

    return saved_count


def run_crawl_action(engine: Engine, max_pages: int) -> int:
    try:
        items = crawl_quotes(max_pages)
        saved_count = save_quotes(engine, items)
    except RuntimeError as exc:
        print(f"错误: {exc}")
        return 1

    print("爬取完成")
    print(f"爬取页数: {max_pages} 页")
    print(f"本次解析: {len(items)} 条")
    print(f"新增保存: {saved_count} 条")
    return 0


def main() -> int:
    engine = get_engine(DB_URL)
    try:
        init_db(engine)
    except SQLAlchemyError as exc:
        print(f"数据库连接或初始化失败: {exc}")
        return 1

    return run_crawl_action(engine, MAX_PAGES)

if __name__ == "__main__":
    main()

