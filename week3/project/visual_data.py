from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# ==================== 常量配置 ====================
DATA_PATH = Path("data.xlsx")  # 数据文件路径
TARGET_COL = "Response"       # 目标变量（标签列）名称
DPI = 300                      # 导出图像的分辨率
TOP_N = 20                     # 针对高基数类别特征，仅分析频次前 N 的类别


def resolve_column(df: pd.DataFrame, *candidates: str) -> str:
    """
    解析并匹配列名（处理列名大小写或拼写不一致的问题）。
    
    在传入的候选列名列表中，返回第一个存在于 DataFrame 中的列名；
    若均不存在则抛出 KeyError 异常。
    """
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    raise KeyError(f"缺少预期的列，已尝试匹配: {', '.join(candidates)}")


def save_plot(filename: str) -> None:
    """
    统一的图像保存与清理工具函数。
    
    自动调整布局、保存高分辨率图片并关闭当前 figure，防止内存泄露。
    """
    plt.tight_layout()
    plt.savefig(filename, dpi=DPI, bbox_inches="tight")
    plt.close()


def plot_missing_rate(df: pd.DataFrame) -> None:
    """绘制各特征的缺失值比例条形图。"""
    # 计算各列的缺失率并按从高到低排序
    missing_rate = df.isna().mean().sort_values(ascending=False)

    plt.figure(figsize=(10, 6))
    sns.barplot(x=missing_rate.values, y=missing_rate.index)
    plt.title("Missing Rate by Feature")  # 各特征缺失率
    save_plot("01_missing_rate.png")


def plot_response_distribution(df: pd.DataFrame) -> None:
    """绘制目标变量（Response，是否响应/购买）的频次分布图。"""
    plt.figure(figsize=(6, 4))
    sns.countplot(x=TARGET_COL, data=df)
    plt.title("Target Variable (Response) Distribution")  # 目标变量分布
    save_plot("02_response_distribution.png")


def plot_correlation_matrix(df: pd.DataFrame, columns: list[str]) -> None:
    """绘制连续数值型特征的热力图/相关系数矩阵。"""
    # 筛选出实际存在于 DataFrame 中的列
    existing_columns = [column for column in columns if column in df.columns]
    if len(existing_columns) < 2:
        return  # 特征少于 2 个时无法计算相关系数，直接返回

    # 计算 Pearson 相关系数（仅针对数值类型）
    corr_df = df.loc[:, existing_columns].corr(numeric_only=True)
    
    plt.figure(figsize=(8, 6))
    sns.heatmap(corr_df, annot=True, cmap="coolwarm", fmt=".2f")
    plt.title("Continuous Feature Correlation Matrix")  # 连续特征相关性矩阵
    save_plot("03_correlation_matrix.png")


def plot_numeric_feature(df: pd.DataFrame, column: str, title: str, prefix: str) -> None:
    """将数值型特征的分布直方图和箱线图合并为一张多子图。"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    sns.histplot(data=df, x=column, kde=True, ax=axes[0])
    axes[0].set_title(f"Distribution of {title}")

    sns.boxplot(data=df, x=column, ax=axes[1])
    axes[1].set_title(f"Boxplot for {title}")

    fig.tight_layout()
    fig.savefig(f"{prefix}_{column.lower()}_summary.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def plot_category_by_response(df: pd.DataFrame, column: str, title: str, filename: str) -> None:
    """绘制分类特征在不同目标响应类别（Response）下的计数对比柱状图（Grouped Countplot）。"""
    plt.figure(figsize=(8, 5))
    sns.countplot(x=column, hue=TARGET_COL, data=df)
    plt.title(f"{title} by Response")
    save_plot(filename)


def plot_category_response_grid(
    df: pd.DataFrame,
    features: list[tuple[str, str]],
    filename: str,
) -> None:
    """将多个低基数分类特征与 Response 的关系合并为一张多子图。"""
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    axes_flat = axes.ravel()

    for ax, (column, title) in zip(axes_flat, features):
        sns.countplot(x=column, hue=TARGET_COL, data=df, ax=ax)
        ax.set_title(f"{title} by Response")
        ax.tick_params(axis="x", rotation=30)

    for ax in axes_flat[len(features):]:
        ax.remove()

    fig.tight_layout()
    fig.savefig(filename, dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def plot_top_category(df: pd.DataFrame, column: str, title: str, prefix: str) -> None:
    """
    针对高基数（类别较多）的分类特征进行分析：
    1. 绘制出现频次前 TOP_N 个类别的样本数量分布图；
    2. 绘制这 TOP_N 个类别对应的目标变量响应率（Response Rate）柱状图。
    """
    # 获取出现频次最高的前 TOP_N 个类别名称
    top_values: list[Any] = df[column].value_counts().head(TOP_N).index.tolist()
    # 过滤出仅包含 TOP_N 类别的子集

    response_rates = [
        float(df.loc[df[column] == value, TARGET_COL].mean())
        for value in top_values
    ]

    fig, axes = plt.subplots(1, 2, figsize=(18, 6))

    sns.countplot(x=column, data=df, order=top_values, ax=axes[0])
    axes[0].set_title(f"Top {TOP_N} {title} Count")
    axes[0].tick_params(axis="x", rotation=45)

    sns.barplot(x=top_values, y=response_rates, ax=axes[1])
    axes[1].set_title(f"Response Rate of Top {TOP_N} {title}")
    axes[1].set_ylabel("Response Rate")
    axes[1].tick_params(axis="x", rotation=45)

    fig.tight_layout()
    fig.savefig(f"{prefix}_{column.lower()}_summary.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    # 1. 读取 Excel 数据集
    df = pd.read_excel(DATA_PATH)

    # 2. 动态匹配可能存在大小写差异的列名
    age_col = resolve_column(df, "Age", "age")
    gender_col = resolve_column(df, "Gender", "gender")

    # 3. 基础探索分析：缺失率与目标变量分布
    plot_missing_rate(df)
    plot_response_distribution(df)
    
    # 4. 连续特征的相关性分析
    plot_correlation_matrix(df, [age_col, "Annual_Premium", "Vintage"])

    # 5. 数值型特征的单变量分布与异常值检测分析
    numeric_features = [
        (age_col, "Age", "04"),
        ("Annual_Premium", "Annual Premium", "05"),
        ("Vintage", "Vintage", "06"),
    ]
    for column, title, prefix in numeric_features:
        plot_numeric_feature(df, column, title, prefix)

    # 6. 低基数分类特征与目标变量的交叉分析
    category_response_features = [
        ("Vehicle_Age", "Vehicle Age", "07_vehicle_age_by_response.png"),
        (gender_col, "Gender", "08_gender_by_response.png"),
        ("Vehicle_Damage", "Vehicle Damage", "09_vehicle_damage_by_response.png"),
        ("Previously_Insured", "Previously Insured", "10_previously_insured_by_response.png"),
        ("Driving_License", "Driving License", "11_driving_license_by_response.png"),
    ]
    plot_category_response_grid(
        df,
        [(column, title) for column, title, _ in category_response_features],
        "07_11_category_by_response_summary.png",
    )

    # 7. 高基数分类特征（地区代码、销售渠道）的前 N 项频次与响应率分析
    top_category_features = [
        ("Region_Code", "Region Code", "12"),
        ("Policy_Sales_Channel", "Policy Sales Channel", "13"),
    ]
    for column, title, prefix in top_category_features:
        plot_top_category(df, column, title, prefix)


if __name__ == "__main__":
    main()
