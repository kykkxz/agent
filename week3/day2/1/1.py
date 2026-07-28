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
sns.histplot(data=tips, x="tip", kde=True, bins=30)
plt.title("小费金额分布直方图（含核密度曲线）")
plt.xlabel("tip")
plt.ylabel("count")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "exercise_01_tip_hist.png"))
plt.close()
