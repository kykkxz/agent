import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# 一、基础配置
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial Unicode MS"]
plt.rcParams["font.weight"] = "normal"
plt.rcParams["axes.unicode_minus"] = False


# 二、读取数据
df = pd.read_csv("StudentsPerformance.csv")
score_columns = ["math_score", "reading_score", "writing_score"]
subject_labels = ["数学", "阅读", "写作"]


# 三、创建 2 行 3 列整合画布
plt.figure(figsize=(18, 10))


# 任务1：三科成绩分布对比
plt.subplot(2, 3, 1)
hist_colors = ["#4C78A8", "#F58518", "#54A24B"]
for column, label, color in zip(score_columns, subject_labels, hist_colors):
    plt.hist(
        df[column],
        bins=12,
        alpha=0.55,
        edgecolor="black",
        color=color,
        label=label,
    )
plt.title("三科成绩分布对比")
plt.xlabel("分数")
plt.ylabel("人数")
plt.grid(axis="y", linestyle="--", alpha=0.4)
plt.legend()


# 任务2：有无考前辅导成绩对比
plt.subplot(2, 3, 2)
prep_order = ["none", "completed"]
prep_labels = ["未参加辅导", "完成辅导"]
prep_means = df.groupby("test_preparation_course")[score_columns].mean().loc[prep_order]  # type: ignore

x = np.arange(len(subject_labels))
bar_width = 0.35
for index, (prep_key, prep_label) in enumerate(zip(prep_order, prep_labels)):
    values = prep_means.loc[prep_key].values
    positions = x + (index - 0.5) * bar_width
    bars = plt.bar(positions, values, width=bar_width, label=prep_label)
    for bar in bars:
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            height + 1,
            f"{height:.1f}",
            ha="center",
            va="bottom",
            fontsize=9,
        )

plt.title("有无考前辅导成绩对比")
plt.xlabel("科目")
plt.ylabel("平均分")
plt.xticks(x, subject_labels)
plt.ylim(0, 100)
plt.grid(axis="y", linestyle="--", alpha=0.4)
plt.legend()


# 任务3：阅读与写作相关性
plt.subplot(2, 3, 3)
gender_styles = {
    "male": ("男生", "#1F77B4"),
    "female": ("女生", "#D62728"),
}
for gender, (label, color) in gender_styles.items():
    gender_data = df[df["gender"] == gender]
    plt.scatter(
        gender_data["reading_score"],
        gender_data["writing_score"],
        alpha=0.55,
        s=25,
        color=color,
        label=label,
    )

fit_x = df["reading_score"]
fit_y = df["writing_score"]
slope, intercept = np.polyfit(fit_x, fit_y, 1)
line_x = np.linspace(fit_x.min(), fit_x.max(), 100)
line_y = slope * line_x + intercept
correlation = fit_x.corr(fit_y)  # type: ignore
plt.plot(line_x, line_y, color="black", linewidth=2, label="线性拟合")
plt.text(
    0.05,
    0.95,
    f"相关系数 r = {correlation:.2f}",
    transform=plt.gca().transAxes,
    ha="left",
    va="top",
    bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.8},
)
plt.title("阅读与写作相关性")
plt.xlabel("阅读分数")
plt.ylabel("写作分数")
plt.grid(linestyle="--", alpha=0.35)
plt.legend()


# 任务4：学生午餐类型样本占比
plt.subplot(2, 3, 4)
lunch_counts = df["lunch"].value_counts()
lunch_label_map = {
    "standard": "标准餐",
    "free/reduced": "减免餐",
}
lunch_labels = [lunch_label_map[item] for item in lunch_counts.index] # type: ignore
explode = [0.08 if value == lunch_counts.max() else 0 for value in lunch_counts.values]
plt.pie(
    lunch_counts.values,  # type: ignore
    labels=lunch_labels,
    autopct="%1.1f%%",
    startangle=90,
    shadow=True,
    explode=explode,
    colors=["#72B7B2", "#E45756"],
)
plt.title("学生午餐类型样本占比")
plt.axis("equal")


# 任务5：家长学历与平均分变化趋势
plt.subplot(2, 3, 5)
education_order = [
    "some high school",
    "high school",
    "some college",
    "associate's degree",
    "bachelor's degree",
    "master's degree",
]
education_labels = ["部分高中", "高中", "部分大学", "副学士", "学士", "硕士"]
education_means = (
    df.groupby("parental_level_of_education")[score_columns]
    .mean()
    .loc[education_order] # type: ignore
)

line_styles = [
    ("math_score", "数学", "#4C78A8", "o"),
    ("reading_score", "阅读", "#F58518", "s"),
    ("writing_score", "写作", "#54A24B", "^"),
]
for column, label, color, marker in line_styles:
    plt.plot(
        education_labels,
        education_means[column].values,
        color=color,
        marker=marker,
        linewidth=2,
        label=label,
    )

plt.title("家长学历与平均分变化趋势")
plt.xlabel("家长学历")
plt.ylabel("平均分")
plt.ylim(0, 100)
plt.xticks(rotation=25, ha="right")
plt.grid(linestyle="--", alpha=0.35)
plt.legend()


# 任务6：空白子图留白
plt.subplot(2, 3, 6)
plt.axis("off")


# 四、保存整合大图
plt.suptitle("学生成绩综合可视化分析", fontsize=18, fontweight="bold")
plt.tight_layout(rect=[0, 0, 1, 0.96]) # type: ignore
plt.savefig("学生成绩综合可视化大图.png", dpi=300, bbox_inches="tight")
plt.show()
