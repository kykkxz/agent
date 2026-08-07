"""职位查询 MCP 服务。"""

from mcp.server.fastmcp import FastMCP


mcp = FastMCP("JobsServer")

JOBS = [
    {
        "title": "Python 工程师",
        "company": "星云科技",
        "salary": "20k-30k",
        "skills": "Python、LangChain、FastAPI",
    },
    {
        "title": "Java 工程师",
        "company": "远航软件",
        "salary": "18k-28k",
        "skills": "Java、Spring Cloud、MySQL",
    },
    {
        "title": "AI 算法工程师",
        "company": "智行人工智能",
        "salary": "25k-40k",
        "skills": "Python、机器学习、大模型",
    },
    {
        "title": "前端工程师",
        "company": "云端互联",
        "salary": "15k-25k",
        "skills": "Vue、React、TypeScript",
    },
]


@mcp.tool()
def search_jobs(keyword: str) -> str:
    """根据职位关键词搜索匹配的招聘信息。"""
    keyword = keyword.lower()
    results = [
        job
        for job in JOBS
        if keyword in job["title"].lower()
        or keyword in job["company"].lower()
        or keyword in job["skills"].lower()
    ]

    if not results:
        return "没有找到匹配的职位。"

    return "\n".join(
        f"{job['title']} | 公司：{job['company']} | 薪资：{job['salary']} | "
        f"技能：{job['skills']}"
        for job in results
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
