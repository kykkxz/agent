"""公司信息 MCP 服务。"""

from mcp.server.fastmcp import FastMCP


mcp = FastMCP("CompanyServer")

COMPANIES = {
    "星云科技": {
        "industry": "人工智能与软件开发",
        "location": "北京",
        "size": "500-1000人",
        "description": "专注于企业级 AI 应用和智能自动化产品。",
    },
    "远航软件": {
        "industry": "企业软件",
        "location": "上海",
        "size": "1000-2000人",
        "description": "提供企业数字化和云计算解决方案。",
    },
    "智行人工智能": {
        "industry": "人工智能",
        "location": "深圳",
        "size": "200-500人",
        "description": "研发计算机视觉、自然语言处理和大模型产品。",
    },
    "云端互联": {
        "industry": "互联网",
        "location": "杭州",
        "size": "200-500人",
        "description": "提供互联网平台和前端技术服务。",
    },
}


@mcp.tool()
def get_company_info(company_name: str) -> str:
    """查询指定公司的行业、地点、规模和业务简介。"""
    company = COMPANIES.get(company_name)
    if company is None:
        return f"暂未找到公司“{company_name}”的信息。"

    return (
        f"公司：{company_name}\n"
        f"行业：{company['industry']}\n"
        f"地点：{company['location']}\n"
        f"规模：{company['size']}\n"
        f"简介：{company['description']}"
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
