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
sns.kdeplot(data=tips, x="total_bill", hue="smoker", fill=True)
plt.title("总账单核密度图（按是否吸烟分组）")
plt.xlabel("total_bill")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "exercise_02_bill_kde_smoker.png"))
plt.close()
