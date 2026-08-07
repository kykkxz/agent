"""互联网工具 MCP 服务。"""

import json
import os
from pathlib import Path
from urllib.parse import quote

import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP


load_dotenv(Path(__file__).resolve().parent.parent / ".env")

mcp = FastMCP("InternetToolsServer")
API_TOKEN = os.getenv("EXTERNAL_API_TOKEN", "")
API_HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}


def _request_json(
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
) -> str:
    """请求 JSON 接口，并将网络异常转换为工具可读的错误信息。"""
    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        return json.dumps(response.json(), ensure_ascii=False)
    except requests.RequestException as error:
        return json.dumps(
            {"error": f"网络请求失败：{error}"},
            ensure_ascii=False,
        )
    except ValueError:
        return json.dumps(
            {"error": "接口返回的数据不是有效的 JSON"},
            ensure_ascii=False,
        )


@mcp.tool()
def get_ip_info(ip: str) -> str:
    """查询 IP 地址的国家、地区、城市、运营商和时区信息。

    参数：
        ip: 要查询的 IPv4 或 IPv6 地址。
    """
    encoded_ip = quote(ip.strip(), safe=".:")
    return _request_json(
        f"http://ip-api.com/json/{encoded_ip}",
        params={"lang": "zh-CN"},
    )


@mcp.tool()
def get_random_fact() -> str:
    """获取一条随机毒鸡汤。"""
    return _request_json(
        "https://v2.xxapi.cn/api/dujitang",
        headers=API_HEADERS,
    )


@mcp.tool()
def search_wikipedia(keyword: str) -> str:
    """获取中文维基百科中指定关键词的页面摘要。

    参数：
        keyword: 要搜索的百科词条名称。
    """
    encoded_keyword = quote(keyword.strip(), safe="")
    return _request_json(
        f"https://zh.wikipedia.org/api/rest_v1/page/summary/{encoded_keyword}"
    )


@mcp.tool()
def get_time_zone(location: str) -> str:
    """查询时区名称和指定时区的当前时间。

    参数：
        location: IANA 时区名称，例如 Asia/Shanghai、Asia/Tokyo 或
            America/New_York。
    """
    return _request_json(
        "https://timeapi.io/api/Time/current/zone",
        params={"timeZone": location},
    )


@mcp.tool()
def get_domain_info(domain: str) -> str:
    """查询域名的注册状态、名称服务器和注册信息。

    参数：
        domain: 要查询的域名，例如 example.com。
    """
    encoded_domain = quote(domain.strip(), safe=".")
    return _request_json(f"https://rdap.org/domain/{encoded_domain}")


if __name__ == "__main__":
    mcp.run(transport="stdio")
