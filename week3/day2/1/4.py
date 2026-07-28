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
sns.violinplot(data=tips, x="day", y="tip", hue="time", split=True)
plt.title("每日小费小提琴图（按时段分组并分割显示）")
plt.xlabel("day")
plt.ylabel("tip")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "exercise_04_tip_violin_day_time.png"))
plt.close()
