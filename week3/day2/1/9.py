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

fig, axes = plt.subplots(2, 1, figsize=(8, 10))

sns.kdeplot(data=tips, x="total_bill", fill=True, ax=axes[0])
axes[0].set_title("账单密度核密度图")

sns.barplot(data=tips, x="sex", y="tip", errorbar=None, ax=axes[1])
axes[1].set_title("男女平均小费柱状图")

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "exercise_09_subplots_kde_bar.png"))
plt.close()
