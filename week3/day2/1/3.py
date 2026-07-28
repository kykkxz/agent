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
sns.boxplot(data=tips, x="time", y="tip", hue="sex")
plt.title("不同用餐时段小费箱线图（按性别分组）")
plt.xlabel("time")
plt.ylabel("tip")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "exercise_03_tip_box_time_sex.png"))
plt.close()
