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

plt.figure(figsize=(8, 6))
sns.barplot(data=tips, x="day", y="tip", errorbar=None)
plt.title("每日小费柱状图（不显示误差线）")
plt.xlabel("day")
plt.ylabel("tip")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "exercise_05_tip_bar_day.png"))
plt.close()
