import os

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "exercise_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

tips = pd.read_csv(os.path.join(BASE_DIR, "tip.csv"))

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

sns.violinplot(data=tips, x="sex", y="total_bill", ax=axes[0])
axes[0].set_title("男女消费金额分布小提琴图")

day_order = ["Thur", "Fri", "Sat", "Sun"]
sns.barplot(
    data=tips, x="day", y="total_bill", order=day_order, errorbar=None, ax=axes[1]
)
axes[1].set_title("一周每日平均消费柱状图")

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "exercise_10_subplots_violin_bar.png"))
plt.close()
