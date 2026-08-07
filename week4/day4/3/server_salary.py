"""薪资计算 MCP 服务。"""

from mcp.server.fastmcp import FastMCP


mcp = FastMCP("SalaryServer")


@mcp.tool()
def calc_salary(base: float, experience_years: int) -> str:
    """按照每年 8% 的涨幅计算工作多年后的薪资。

    base 是初始薪资，experience_years 是工作年限，计算公式为：
    base * (1.08 ** experience_years)。
    """
    salary = base * (1.08 ** experience_years)
    return (
        f"初始薪资：{base:.2f}\n"
        f"工作年限：{experience_years} 年\n"
        f"年涨幅：8%\n"
        f"计算后薪资：{salary:.2f}"
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
